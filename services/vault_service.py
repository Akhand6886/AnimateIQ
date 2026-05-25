import os
import math
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import delete

from models import SemanticChunk
from services.gemini_service import gemini_service

logger = logging.getLogger("VaultService")

class VaultService:
    """
    Manages the local Obsidian-compatible Markdown Vault and Vector Search Engine.
    Handles file persistence, text chunking, and pure-Python semantic vector search.
    """

    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.vault_dir = os.path.join(base_dir, "vault")
        self.memories_dir = os.path.join(self.vault_dir, "memories")
        self.scripts_dir = os.path.join(self.vault_dir, "scripts")
        self.characters_dir = os.path.join(self.vault_dir, "characters")
        
        # Ensure directories exist
        os.makedirs(self.memories_dir, exist_ok=True)
        os.makedirs(self.scripts_dir, exist_ok=True)
        os.makedirs(self.characters_dir, exist_ok=True)

    def write_memory_to_vault(self, key: str, value: List[str]) -> str:
        """Saves a project memory preference as an Obsidian Markdown file."""
        file_path = os.path.join(self.memories_dir, f"{key}.md")
        content = f"# {key}\n\n"
        for val in value:
            content += f"- {val}\n"
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"[Vault] Saved memory to {file_path}")
        return file_path

    def delete_memory_from_vault(self, key: str) -> None:
        """Deletes a project memory preference from the vault."""
        file_path = os.path.join(self.memories_dir, f"{key}.md")
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"[Vault] Deleted memory file: {file_path}")

    def write_script_to_vault(self, series_slug: str, job_id: str, topic: str, draft_text: str) -> str:
        """Saves a completed pipeline script as an Obsidian Markdown file."""
        file_path = os.path.join(self.scripts_dir, f"{series_slug}_{job_id}.md")
        
        # Format with clean frontmatter and headers
        content = (
            f"---\n"
            f"type: script\n"
            f"topic: \"{topic}\"\n"
            f"job_id: {job_id}\n"
            f"series: [[{series_slug}]]\n"
            f"---\n\n"
            f"# {topic} Script\n\n"
            f"{draft_text}\n"
        )
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"[Vault] Saved script to {file_path}")
        return file_path

    def chunk_markdown(self, text: str, max_chunk_size: int = 500) -> List[str]:
        """Splits markdown text into semantic paragraph-level chunks for embedding."""
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_length = 0
        
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            
            # If paragraph itself is huge, yield existing and split it by sentences
            if len(p) > max_chunk_size:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0
                chunks.append(p)
                continue

            if current_length + len(p) > max_chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [p]
                current_length = len(p)
            else:
                current_chunk.append(p)
                current_length += len(p) + 2 # Add length for the separator newlines
                
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
            
        return chunks

    async def index_file(self, file_path: str, db: Session) -> None:
        """Parses, chunks, generates embeddings, and saves a markdown file to the database index."""
        # Use relative path for database storage consistency
        rel_path = os.path.relpath(file_path, self.base_dir)
        
        if not os.path.exists(file_path):
            logger.warning(f"[Vault] Cannot index non-existent file: {file_path}")
            return
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        chunks = self.chunk_markdown(content)
        if not chunks:
            logger.info(f"[Vault] File {rel_path} is empty. Skipping index.")
            return

        # Delete any existing chunks for this file
        db.execute(delete(SemanticChunk).where(SemanticChunk.file_path == rel_path))
        db.commit()
        
        logger.info(f"[Vault] Indexing {len(chunks)} chunks for {rel_path}...")
        
        for idx, text in enumerate(chunks):
            # Clean headers or frontmatter markers slightly for cleaner embedding input
            clean_text = text.replace("---", "").strip()
            embedding = await gemini_service.generate_embedding(clean_text)
            
            chunk_record = SemanticChunk(
                file_path=rel_path,
                chunk_index=idx,
                text_content=text,
                embedding_json=embedding
            )
            db.add(chunk_record)
            
        db.commit()
        logger.info(f"[Vault] Successfully indexed: {rel_path}")

    async def reindex_vault(self, db: Session) -> Dict[str, Any]:
        """Scans the vault directory and re-indexes all markdown files."""
        md_files = []
        for root, _, files in os.walk(self.vault_dir):
            for file in files:
                if file.endswith(".md"):
                    md_files.append(os.path.join(root, file))
        
        indexed_count = 0
        for filepath in md_files:
            try:
                await self.index_file(filepath, db)
                indexed_count += 1
            except Exception as e:
                logger.error(f"[Vault] Failed to index file {filepath}: {e}", exc_info=True)
                
        # Clean up database records of files that no longer exist on disk
        all_chunks = db.query(SemanticChunk.file_path).distinct().all()
        deleted_count = 0
        for (rel_path,) in all_chunks:
            full_path = os.path.join(self.base_dir, rel_path)
            if not os.path.exists(full_path):
                logger.info(f"[Vault] File no longer exists, purging chunks: {rel_path}")
                db.execute(delete(SemanticChunk).where(SemanticChunk.file_path == rel_path))
                deleted_count += 1
                
        if deleted_count > 0:
            db.commit()
            
        return {
            "status": "success",
            "indexed_files": indexed_count,
            "purged_files": deleted_count
        }

    async def search(self, query: str, db: Session, top_k: int = 3) -> List[Dict[str, Any]]:
        """Performs semantic vector search over the vault chunks using pure-Python cosine similarity."""
        query_vector = await gemini_service.generate_embedding(query)
        
        # Load all chunks from the database
        chunks = db.query(SemanticChunk).all()
        if not chunks:
            return []

        results = []
        for chunk in chunks:
            # Read vector from SQLite JSON field
            chunk_vector = chunk.embedding_json
            if not chunk_vector or len(chunk_vector) != len(query_vector):
                continue
                
            # Cosine similarity logic
            dot_prod = sum(x * y for x, y in zip(query_vector, chunk_vector))
            mag1 = math.sqrt(sum(x * x for x in query_vector))
            mag2 = math.sqrt(sum(x * x for x in chunk_vector))
            
            score = 0.0
            if mag1 > 0 and mag2 > 0:
                score = dot_prod / (mag1 * mag2)
                
            results.append({
                "file_path": chunk.file_path,
                "chunk_index": chunk.chunk_index,
                "text_content": chunk.text_content,
                "score": score
            })
            
        # Sort descending by score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

# Persistent singleton instance
vault_service = VaultService(base_dir="/Users/alpha/Desktop/antigavity/datausingIDE")
