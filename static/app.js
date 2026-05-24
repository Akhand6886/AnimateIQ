document.addEventListener('DOMContentLoaded', () => {
    // --- State ---
    let activeJobId = null;
    let activeJobTimer = null;
    let selectedStepId = null;
    let storyboardSlides = [];
    let playbackInterval = null;
    let currentSlideIndex = 0;

    // DOM Elements
    const tabButtons = document.querySelectorAll('.nav-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    const pageTitle = document.getElementById('page-title');
    const pageDesc = document.getElementById('page-desc');
    const rawPromptText = document.getElementById('raw-prompt');
    const btnParsePrompt = document.getElementById('btn-parse-prompt');
    const parseSpinner = document.getElementById('parse-spinner');
    
    // Structured task form inputs
    const structuredCard = document.getElementById('structured-task-card');
    const taskTopic = document.getElementById('task-topic');
    const taskPlatform = document.getElementById('task-platform');
    const taskDuration = document.getElementById('task-duration');
    const taskStyle = document.getElementById('task-style');
    const taskAssets = document.getElementById('task-assets');
    const btnRunHarness = document.getElementById('btn-run-harness');

    // Execution elements
    const executionTimeline = document.getElementById('execution-timeline');
    const executionJobLbl = document.getElementById('execution-job-lbl');
    const evalBadge = document.getElementById('eval-badge');
    const metricFact = document.getElementById('metric-fact');
    const metricStyle = document.getElementById('metric-style');
    const metricEngagement = document.getElementById('metric-engagement');
    const auditErrorsContainer = document.getElementById('audit-errors-container');
    const auditErrorsList = document.getElementById('audit-errors-list');
    const terminalStdout = document.getElementById('terminal-stdout');
    
    // Final output elements
    const finalOutputCard = document.getElementById('final-output-card');
    const outputPackageType = document.getElementById('output-package-type');
    const outputSeoTitle = document.getElementById('output-seo-title');
    const outputSlug = document.getElementById('output-slug');
    const outputScriptText = document.getElementById('output-script-text');
    const outputMetaDescription = document.getElementById('output-meta-description');
    const outputKeywords = document.getElementById('output-keywords');
    const outputTags = document.getElementById('output-tags');
    const subtabButtons = document.querySelectorAll('.tab-sub-btn');
    const subtabContents = document.querySelectorAll('.tab-sub-content');

    // Media elements
    const videoCanvasSlide = document.getElementById('video-canvas-slide');
    const videoCanvasOverlay = document.getElementById('video-canvas-overlay');
    const btnVideoPlay = document.getElementById('btn-video-play');
    const videoScrubFill = document.getElementById('video-scrub-fill');
    const videoTime = document.getElementById('video-time');
    const videoAudioPreview = document.getElementById('video-audio-preview');

    // Memory Store Elements
    const memoryCardsContainer = document.getElementById('memory-cards-container');
    const btnSaveMemories = document.getElementById('btn-save-memories');
    const saveMemSpinner = document.getElementById('save-mem-spinner');

    // Job history elements
    const jobsTableBody = document.getElementById('jobs-table-body');

    // 1. Tab Switching Handler
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.getAttribute('data-tab');
            switchTab(tabId);
        });
    });

    function switchTab(tabId) {
        tabButtons.forEach(b => {
            if (b.getAttribute('data-tab') === tabId) {
                b.classList.add('active');
            } else {
                b.classList.remove('active');
            }
        });
        
        tabPanes.forEach(pane => {
            if (pane.id === `tab-${tabId}`) {
                pane.classList.add('active');
            } else {
                pane.classList.remove('active');
            }
        });

        // Update Headers
        if (tabId === 'orchestrator') {
            pageTitle.textContent = "Executive Orchestrator";
            pageDesc.textContent = "Transform raw AI prompts into a structured thinking machine ecosystem.";
        } else if (tabId === 'execution') {
            pageTitle.textContent = "Active Execution Loop";
            pageDesc.textContent = "Monitor the real-time agent execution plan timeline and log outputs.";
            const execBadge = document.getElementById('execution-badge');
            if (execBadge) execBadge.classList.add('hidden');
            selectedStepId = null;  // Reset step inspection on tab re-entry
        } else if (tabId === 'memory') {
            pageTitle.textContent = "Cumulative Preference Memory";
            pageDesc.textContent = "Manage SQLite persistent guidelines, style preferences, and banned words.";
            loadMemorySettings();
        } else if (tabId === 'history') {
            pageTitle.textContent = "Job Archives";
            pageDesc.textContent = "Track execution results and details of past and historical pipeline runs.";
            loadJobsHistory();
        }
    }

    // Sub-tab switcher inside output representation
    subtabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const subtabId = btn.getAttribute('data-subtab');
            subtabButtons.forEach(b => b.classList.toggle('active', b === btn));
            subtabContents.forEach(pane => {
                pane.classList.toggle('active', pane.id === `subtab-${subtabId}`);
            });
        });
    });

    // 2. Interface Layer: Prompt Parsing
    btnParsePrompt.addEventListener('click', async () => {
        const text = rawPromptText.value.trim();
        if (!text) return alert("Please input a prompt to parse.");

        parseSpinner.classList.remove('hidden');
        btnParsePrompt.disabled = true;

        try {
            const response = await fetch('/api/harness/parse', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: text })
            });

            if (!response.ok) throw new Error("Parser endpoint returned error code.");
            
            const task = await response.json();
            
            // Populate task inputs
            taskTopic.value = task.topic;
            taskPlatform.value = task.target_platform;
            taskDuration.value = task.duration;
            taskStyle.value = task.style;
            
            // Populate assets
            taskAssets.innerHTML = '';
            task.assets_needed.forEach(asset => {
                const badge = document.createElement('span');
                badge.className = 'tag';
                badge.textContent = asset;
                taskAssets.appendChild(badge);
            });

            // Enable Run Card
            structuredCard.classList.remove('disabled');
            btnRunHarness.disabled = false;

        } catch (error) {
            console.error("Parse Error:", error);
            alert("Failed to parse prompt. Using default task structure.");
            // Set defaults
            taskTopic.value = "Anime Spot";
            taskPlatform.value = "Editorial Blog";
            taskDuration.value = "800 words";
            taskStyle.value = "high-energy";
            taskAssets.innerHTML = '<span class="tag">Script</span><span class="tag">Thumbnail</span>';
            structuredCard.classList.remove('disabled');
            btnRunHarness.disabled = false;
        } finally {
            parseSpinner.classList.add('hidden');
            btnParsePrompt.disabled = false;
        }
    });

    // 3. Trigger Intelligence Harness Running
    btnRunHarness.addEventListener('click', async () => {
        const payload = {
            topic: taskTopic.value,
            target_platform: taskPlatform.value,
            duration: taskDuration.value,
            style: taskStyle.value,
            assets_needed: Array.from(taskAssets.querySelectorAll('.tag')).map(t => t.textContent)
        };

        try {
            const response = await fetch('/api/harness/trigger', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) throw new Error("Job launch endpoint failed.");

            const job = await response.json();
            activeJobId = job.id;
            
            // Switch tabs
            switchTab('execution');
            
            // Update navigation indicator badge
            const executionBadge = document.getElementById('execution-badge');
            executionBadge.textContent = "RUNNING";
            executionBadge.classList.remove('hidden');

            // Setup logs and timeline empty state
            executionTimeline.innerHTML = '<div class="timeline-empty"><div class="spinner"></div><p>Decomposing goals and generating execution steps...</p></div>';
            terminalStdout.textContent = "Executive Planner wakes up. Initiating dynamic multi-agent planning...";
            
            // Start Poller
            startJobPoller(activeJobId);

        } catch (error) {
            console.error("Trigger Job Error:", error);
            alert("Could not start harness loop.");
        }
    });

    // 4. Job Poller Runtime
    function startJobPoller(jobId) {
        if (activeJobTimer) clearInterval(activeJobTimer);
        
        // Immediate fetch
        pollJobState(jobId);
        
        // Interval poll
        activeJobTimer = setInterval(() => {
            pollJobState(jobId);
        }, 2000);
    }

    async function pollJobState(jobId) {
        try {
            const response = await fetch(`/api/jobs/${jobId}`);
            if (!response.ok) throw new Error("Polling job fetch error.");
            
            const job = await response.json();
            updateExecutionUI(job);
            
            if (job.status === 'completed' || job.status === 'failed') {
                clearInterval(activeJobTimer);
                activeJobTimer = null;
                const badge = document.getElementById('execution-badge');
                badge.textContent = job.status.toUpperCase();
                badge.style.backgroundColor = job.status === 'completed' ? 'var(--success)' : 'var(--danger)';
            }
        } catch (error) {
            console.error("Poll Error:", error);
        }
    }

    // 5. Update Active Execution Panel Elements
    function updateExecutionUI(job) {
        executionJobLbl.textContent = `Job ID: ${job.id} | Series: ${job.series_title} (${job.target_type})`;
        
        // Render Timeline Plan Steps
        const steps = job.execution_plan || [];
        if (steps.length === 0) return;

        executionTimeline.innerHTML = '';
        steps.forEach((step, idx) => {
            const node = document.createElement('div');
            node.className = `timeline-node ${step.status}`;
            node.setAttribute('data-step-id', step.step_id);
            node.innerHTML = `
                <h4>${idx + 1}. ${step.name}</h4>
                <p>Worker: <code>${step.worker}</code> | Status: ${step.status}</p>
            `;
            
            // Timeline step click inspection
            node.addEventListener('click', () => {
                selectedStepId = step.step_id;
                document.querySelectorAll('.timeline-node').forEach(n => n.style.borderColor = 'transparent');
                node.style.borderColor = 'var(--accent)';
                
                // Show output and logs in console terminal
                terminalStdout.textContent = `[INSPECTION STEP: ${step.name.toUpperCase()}]\n\n--- OUTPUT STRUCTURE ---\n${step.output || 'No output recorded yet.'}\n\n--- WORKER LOGS ---\n${step.log || 'Waiting for execution logs...'}`;
            });

            executionTimeline.appendChild(node);
        });

        // Set default console text scrolling to active node if not manually inspecting
        if (!selectedStepId) {
            const activeStep = steps.find(s => s.status === 'running') || steps.find(s => s.status === 'completed' && s.log);
            if (activeStep) {
                terminalStdout.textContent = `[AGENT LOGS: ${activeStep.name.toUpperCase()}]\n\n${activeStep.log}`;
                // Auto scroll terminal to bottom
                const termBody = document.querySelector('.terminal-body');
                termBody.scrollTop = termBody.scrollHeight;
            }
        }

        // Render evaluations (Layer 6)
        const evals = job.evaluations || {};
        if (Object.keys(evals).length > 0) {
            evalBadge.textContent = evals.passed ? "PASSED" : "FAILED STYLE/FACT AUDIT";
            evalBadge.style.backgroundColor = evals.passed ? 'var(--success)' : 'var(--danger)';
            metricFact.textContent = evals.fact_accuracy_score ? `${evals.fact_accuracy_score}/10` : '-';
            metricStyle.textContent = evals.style_compliance_score ? `${evals.style_compliance_score}/10` : '-';
            metricEngagement.textContent = evals.predicted_engagement_score ? `${evals.predicted_engagement_score}%` : '-';

            if (evals.errors && evals.errors.length > 0) {
                auditErrorsContainer.classList.remove('hidden');
                auditErrorsList.innerHTML = '';
                evals.errors.forEach(err => {
                    const li = document.createElement('li');
                    li.textContent = err;
                    auditErrorsList.appendChild(li);
                });
            } else {
                auditErrorsContainer.classList.add('hidden');
            }
        } else {
            evalBadge.textContent = "PENDING";
            evalBadge.style.backgroundColor = 'var(--border-color)';
            metricFact.textContent = '-';
            metricStyle.textContent = '-';
            metricEngagement.textContent = '-';
            auditErrorsContainer.classList.add('hidden');
        }

        // If completed, show deliverables representations
        if (job.status === 'completed') {
            finalOutputCard.classList.remove('hidden');
            outputPackageType.textContent = job.target_type === 'youtube_short' ? "YouTube Short Video Deliverable" : "Contentful Editorial Article Deliverable";
            
            // Map nested outputs
            const writerData = job.writer_data || {};
            const seoData = job.seo_data || {};
            const formatterData = job.formatter_data || {};
            const publisherData = job.publisher_data || {};

            outputSeoTitle.textContent = seoData.seo_title || writerData.draft_title || "Review Draft Completed";
            outputSlug.textContent = seoData.slug || "n/a";
            
            outputScriptText.textContent = writerData.draft_text || writerData.review_body_markdown || "Content text body complete.";
            outputMetaDescription.textContent = seoData.meta_description || "n/a";
            outputKeywords.textContent = seoData.keywords ? seoData.keywords.join(', ') : 'n/a';
            outputTags.textContent = seoData.tags ? seoData.tags.join(', ') : 'n/a';

            // Storyboard video rendering
            const pubAssets = publisherData.assets || {};
            const thumbUrl = pubAssets.thumbnail || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800";
            const audioUrl = pubAssets.audio || "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3";
            
            videoCanvasSlide.src = thumbUrl;
            videoAudioPreview.src = audioUrl;

            // Load storyboard slides from steps if available (e.g. voice_timing output)
            const timingStep = steps.find(s => s.worker === 'voice_timing');
            if (timingStep && timingStep.output) {
                try {
                    const parsedOut = JSON.parse(timingStep.output);
                    storyboardSlides = parsedOut.timing_map || [];
                    if (storyboardSlides.length > 0) {
                        videoCanvasOverlay.textContent = storyboardSlides[0].subtitle || "Narration ready.";
                    }
                } catch(e) {
                    storyboardSlides = [];
                    videoCanvasOverlay.textContent = "Playback content compiled.";
                }
            } else {
                storyboardSlides = [];
                videoCanvasOverlay.textContent = "Audio slide compile complete.";
            }

        } else {
            finalOutputCard.classList.add('hidden');
        }
    }

    // 6. Audio Storyboard Synchronization Playback Loops
    btnVideoPlay.addEventListener('click', () => {
        if (videoAudioPreview.paused) {
            videoAudioPreview.play();
            btnVideoPlay.textContent = "Pause Short";
            startStoryboardPlaybackTimer();
        } else {
            videoAudioPreview.pause();
            btnVideoPlay.textContent = "Play Short";
            stopStoryboardPlaybackTimer();
        }
    });

    function startStoryboardPlaybackTimer() {
        if (playbackInterval) clearInterval(playbackInterval);
        playbackInterval = setInterval(() => {
            const curTime = videoAudioPreview.currentTime;
            const duration = videoAudioPreview.duration || 60;
            const percentage = (curTime / duration) * 100;
            
            videoScrubFill.style.width = `${percentage}%`;
            
            // Format time display
            const mins = Math.floor(curTime / 60);
            const secs = Math.floor(curTime % 60);
            videoTime.textContent = `${mins}:${secs < 10 ? '0' : ''}${secs}`;

            // Sync visual slides if storyboard timings are loaded
            if (storyboardSlides.length > 0) {
                const activeSlide = storyboardSlides.find((s, idx) => {
                    const start = s.start || idx * 10;
                    const end = s.end || (idx + 1) * 10;
                    return curTime >= start && curTime < end;
                }) || storyboardSlides[storyboardSlides.length - 1];

                if (activeSlide) {
                    videoCanvasOverlay.textContent = activeSlide.subtitle;
                }
            }

            if (videoAudioPreview.ended) {
                btnVideoPlay.textContent = "Play Short";
                videoScrubFill.style.width = "0%";
                videoTime.textContent = "0:00";
                stopStoryboardPlaybackTimer();
            }
        }, 200);
    }

    function stopStoryboardPlaybackTimer() {
        if (playbackInterval) {
            clearInterval(playbackInterval);
            playbackInterval = null;
        }
    }

    // 7. Memory Store management panel load
    async function loadMemorySettings() {
        try {
            const response = await fetch('/api/harness/memory');
            const memories = await response.json();
            
            memoryCardsContainer.innerHTML = '';
            memories.forEach(mem => {
                const box = document.createElement('div');
                box.className = 'memory-box';
                box.innerHTML = `
                    <label>${mem.key.replaceAll('_', ' ')}</label>
                    <p style="font-size:11px; color:var(--text-secondary)">Guidelines separated by comma or newlines.</p>
                    <textarea data-key="${mem.key}" rows="4">${mem.value.join('\n')}</textarea>
                `;
                memoryCardsContainer.appendChild(box);
            });
        } catch (error) {
            console.error("Load Memory Error:", error);
        }
    }

    btnSaveMemories.addEventListener('click', async () => {
        saveMemSpinner.classList.remove('hidden');
        btnSaveMemories.disabled = true;

        const textareas = memoryCardsContainer.querySelectorAll('textarea');
        try {
            for (let ta of textareas) {
                const key = ta.getAttribute('data-key');
                const val = ta.value.split('\n').map(item => item.trim()).filter(item => item.length > 0);
                
                await fetch('/api/harness/memory', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ key: key, value: val })
                });
            }
            alert("Memory configuration updated in database.");
        } catch (error) {
            console.error("Save Memory Error:", error);
            alert("Failed to save memory guidelines.");
        } finally {
            saveMemSpinner.classList.add('hidden');
            btnSaveMemories.disabled = false;
        }
    });

    // 8. Job Archives History Table Loading
    async function loadJobsHistory() {
        try {
            const response = await fetch('/api/jobs');
            const jobs = await response.json();
            
            jobsTableBody.innerHTML = '';
            if (jobs.length === 0) {
                jobsTableBody.innerHTML = '<tr><td colspan="6" class="text-center">No historical execution records found.</td></tr>';
                return;
            }

            jobs.forEach(job => {
                const tr = document.createElement('tr');
                const date = new Date(job.created_at);
                const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

                tr.innerHTML = `
                    <td><code>${job.id.substring(0, 8)}...</code></td>
                    <td><strong>${job.series_title}</strong></td>
                    <td><code>${job.target_type}</code></td>
                    <td>${dateStr}</td>
                    <td><span class="badge-status status-${job.status}">${job.status.toUpperCase()}</span></td>
                    <td><button class="btn btn-small btn-inspect" data-job-id="${job.id}">Inspect</button></td>
                `;

                // Add inspector trigger
                tr.querySelector('.btn-inspect').addEventListener('click', () => {
                    activeJobId = job.id;
                    switchTab('execution');
                    pollJobState(activeJobId);
                });

                jobsTableBody.appendChild(tr);
            });
        } catch (error) {
            console.error("Load Jobs History Error:", error);
            jobsTableBody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Failed to fetch historical database.</td></tr>';
        }
    }

    // 9. Load config status
    async function loadSystemSettings() {
        try {
            const response = await fetch('/api/harness/settings');
            if (response.ok) {
                const config = await response.json();
                const modelBadge = document.querySelector('.model-name');
                if (modelBadge) {
                    modelBadge.textContent = `${config.llm_provider.toUpperCase()} (${config.default_model})`;
                }
            }
        } catch (error) {
            console.error("Failed to load system settings:", error);
        }
    }
    loadSystemSettings();

    // Cleanup intervals on page unload
    window.addEventListener('beforeunload', () => {
        if (activeJobTimer) clearInterval(activeJobTimer);
        if (playbackInterval) clearInterval(playbackInterval);
    });
});
