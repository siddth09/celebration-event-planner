/**
 * Celebrio AI Planner - Client-side Application Logic
 * Implements persona state management, interactive expense tracking,
 * vendor RFP drafting, real-time chat, and live testing sandbox.
 */

document.addEventListener('DOMContentLoaded', () => {
  // State Store
  const state = {
    currentPersona: 'wedding',
    currentPlan: null,
    presets: null,
    chatHistory: [],
    milestonesTotal: 0,
    milestonesCompleted: 0
  };

  // Persona Presets Definitions
  const PERSONA_CONFIGS = {
    wedding: {
      name: "Sarah & Alex Autumn Vineyard Wedding",
      budget: 28000,
      guests: 120,
      location: "Napa Valley, CA",
      date: "2026-10-18",
      theme: "Rustic Chic, Candlelit Evening, Live Acoustic Music",
      tags: ["Rustic Chic", "Black Tie Luxury", "Boho Garden", "Modern Minimalist", "Beachside Sunset"],
      icon: "💍",
      title: "Wedding Celebration Planner",
      desc: "Comprehensive wedding coordination with ceremony, reception, and guest hospitality."
    },
    birthday: {
      name: "Jordan's 30th Milestone Birthday Bash",
      budget: 4500,
      guests: 40,
      location: "Skyline Rooftop Lounge, Chicago",
      date: "2026-11-14",
      theme: "Neon Retro 90s, Custom Cocktail Bar, Photo Booth",
      tags: ["Neon 90s", "Casino Royale", "Tropical Luau", "Roaring 20s", "Cozy Dinner Party"],
      icon: "🎂",
      title: "Milestone Birthday Planner",
      desc: "Memorable celebration designed around the honoree's age milestone and passions."
    },
    community: {
      name: "Oakland Oak & Harvest Community Festival",
      budget: 15000,
      guests: 600,
      location: "Civic Memorial Park, Oakland",
      date: "2026-10-25",
      theme: "Multicultural Food Trucks, Acoustic Stage, Artisan Market",
      tags: ["Food Truck Fair", "Charity 5K", "Artisan Makers", "Cultural Heritage", "Kids STEM Carnival"],
      icon: "🎪",
      title: "Community & Festival Planner",
      desc: "Public gatherings, neighborhood block parties, and cultural festivals with municipal permit coordination."
    },
    custom: {
      name: "Summit Horizon Annual Gala",
      budget: 20000,
      guests: 100,
      location: "Grand Ballroom, Seattle",
      date: "2026-12-05",
      theme: "Black & Gold Elegance, Keynote Stage, Networking Lounge",
      tags: ["Corporate Gala", "Anniversary Celebration", "Alumni Reunion", "Fundraiser Dinner"],
      icon: "✨",
      title: "Custom Celebration Planner",
      desc: "Flexible, high-precision event engine for unique celebrations and gatherings."
    }
  };

  // Elements
  const form = document.getElementById('planner-form');
  const inputEventName = document.getElementById('input-event-name');
  const inputBudget = document.getElementById('input-budget');
  const inputGuests = document.getElementById('input-guests');
  const inputDate = document.getElementById('input-date');
  const inputLocation = document.getElementById('input-location');
  const inputTheme = document.getElementById('input-theme');
  const quickThemeTags = document.getElementById('quick-theme-tags');
  const feedback = document.getElementById('form-validation-feedback');
  const btnSpinner = document.getElementById('btn-spinner');
  const btnText = document.getElementById('btn-text');
  const planDisplay = document.getElementById('plan-display-container');

  // Modals & Drawers
  const modalTest = document.getElementById('modal-test-sandbox');
  const modalRfp = document.getElementById('modal-vendor-rfp');
  const chatDrawer = document.getElementById('chat-drawer');

  // Initialize
  initPersona('wedding');
  checkHealth();

  // -------------------------------------------------------------
  // Persona Switching Logic
  // -------------------------------------------------------------
  document.querySelectorAll('.persona-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      const type = pill.dataset.type;
      initPersona(type);
    });
  });

  function initPersona(type) {
    state.currentPersona = type;
    document.documentElement.setAttribute('data-theme', type);

    // Update active tab styling
    document.querySelectorAll('.persona-pill').forEach(p => {
      const isActive = p.dataset.type === type;
      p.classList.toggle('active', isActive);
      p.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });

    const cfg = PERSONA_CONFIGS[type];
    if (!cfg) return;

    // Update form header display
    document.getElementById('persona-icon-display').textContent = cfg.icon;
    document.getElementById('persona-heading-text').textContent = cfg.title;
    document.getElementById('persona-description-text').textContent = cfg.desc;

    // Prefill form defaults
    inputEventName.value = cfg.name;
    inputBudget.value = cfg.budget;
    inputGuests.value = cfg.guests;
    inputDate.value = cfg.date;
    inputLocation.value = cfg.location;
    inputTheme.value = cfg.theme;

    // Update quick tags
    quickThemeTags.innerHTML = '';
    cfg.tags.forEach(tag => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'tag-chip';
      chip.textContent = tag;
      chip.addEventListener('click', () => {
        inputTheme.value = tag;
      });
      quickThemeTags.appendChild(chip);
    });

    clearError();
  }

  // -------------------------------------------------------------
  // Health & GenAI Status Check
  // -------------------------------------------------------------
  async function checkHealth() {
    try {
      const res = await fetch('/health');
      const data = await res.json();
      const indicator = document.getElementById('ai-status-indicator');
      if (data.genai_active) {
        indicator.innerHTML = '<span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--status-success);"></span> <span>Gemini 1.5 Active</span>';
        indicator.style.color = 'var(--status-success)';
      } else {
        indicator.innerHTML = '<span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--status-info);"></span> <span>Deterministic Engine Active</span>';
        indicator.style.color = 'var(--status-info)';
      }
    } catch (e) {
      console.warn("Health check unreachable, running offline mode.");
    }
  }

  // -------------------------------------------------------------
  // Form Submission & Plan Synthesis
  // -------------------------------------------------------------
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();

    const payload = {
      event_name: inputEventName.value.trim(),
      event_type: state.currentPersona,
      budget: parseFloat(inputBudget.value) || 0,
      guest_count: parseInt(inputGuests.value, 10) || 0,
      event_date: inputDate.value,
      location: inputLocation.value.trim(),
      theme_preference: inputTheme.value.trim()
    };

    // Client-side pre-validation
    if (!payload.event_name) {
      showError("Please enter an event name.");
      inputEventName.focus();
      return;
    }
    if (payload.budget <= 0) {
      showError("Budget must be greater than zero.");
      inputBudget.focus();
      return;
    }
    if (payload.guest_count <= 0) {
      showError("Guest count must be at least 1 person.");
      inputGuests.focus();
      return;
    }

    // Set Loading State
    setLoading(true);

    try {
      const response = await fetch('/api/generate-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.error || "Failed to generate plan.");
      }

      state.currentPlan = data.plan;
      renderPlan(data.plan);
      
      // Scroll smoothly to results
      planDisplay.style.display = 'block';
      planDisplay.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (err) {
      showError(err.message);
    } finally {
      setLoading(false);
    }
  });

  function setLoading(isLoading) {
    btnSpinner.style.display = isLoading ? 'inline-block' : 'none';
    btnText.textContent = isLoading ? 'Synthesizing with AI...' : '✨ Synthesize GenAI Plan';
    document.getElementById('btn-generate-plan').disabled = isLoading;
  }

  function showError(msg) {
    feedback.textContent = `⚠️ ${msg}`;
  }

  function clearError() {
    feedback.textContent = '';
  }

  // -------------------------------------------------------------
  // Rendering Generated Plan
  // -------------------------------------------------------------
  function renderPlan(plan) {
    const meta = plan.event_metadata || {};
    
    // Header summary & financial stats
    document.getElementById('display-event-name').textContent = meta.event_name || 'Celebration Plan';
    document.getElementById('display-plan-source').textContent = plan.source || 'Celebrio GenAI';
    document.getElementById('display-plan-summary').textContent = plan.summary || '';

    updateFinancialMetrics();

    // Render the 4 Pillars
    renderBudgetCategories(plan.budget_breakdown || []);
    renderMilestoneTimeline(plan.milestone_timeline || []);
    renderVendorChecklist(plan.vendor_checklist || []);
    renderPersonalizedIdeas(plan.personalized_ideas || {});
  }

  // -------------------------------------------------------------
  // Financial Metrics & Dynamic Re-calculation
  // -------------------------------------------------------------
  function updateFinancialMetrics() {
    if (!state.currentPlan) return;
    const totalBudget = state.currentPlan.event_metadata.budget || 0;
    const guests = state.currentPlan.event_metadata.guest_count || 1;
    const categories = state.currentPlan.budget_breakdown || [];

    const totalAllocated = categories.reduce((sum, c) => sum + (c.allocated_amount || 0), 0);
    const totalActual = categories.reduce((sum, c) => sum + (c.actual_amount || 0), 0);
    const remaining = totalBudget - totalActual;
    const utilization = totalBudget > 0 ? (totalActual / totalBudget) * 100 : 0;

    document.getElementById('stat-total-budget').textContent = `$${totalBudget.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
    document.getElementById('stat-cost-per-guest').textContent = `$${(totalBudget / guests).toFixed(2)} per guest`;

    document.getElementById('stat-allocated').textContent = `$${totalAllocated.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
    document.getElementById('stat-actual-spent').textContent = `$${totalActual.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
    document.getElementById('stat-actual-utilization').textContent = `${utilization.toFixed(1)}% of budget utilized`;

    const remEl = document.getElementById('stat-remaining');
    const statusEl = document.getElementById('stat-budget-status');
    remEl.textContent = `$${remaining.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;

    if (remaining < 0) {
      remEl.style.color = 'var(--status-danger)';
      statusEl.textContent = `⚠️ Over budget by $${Math.abs(remaining).toFixed(2)}`;
      statusEl.style.color = 'var(--status-danger)';
    } else {
      remEl.style.color = 'var(--status-success)';
      statusEl.textContent = 'Within Budget Reserve';
      statusEl.style.color = 'var(--text-muted)';
    }
  }

  // -------------------------------------------------------------
  // Pillar 1: Dynamic Budget & Expenses
  // -------------------------------------------------------------
  function renderBudgetCategories(categories) {
    const container = document.getElementById('budget-category-container');
    container.innerHTML = '';

    categories.forEach((cat, idx) => {
      const card = document.createElement('div');
      card.className = 'category-card';

      const actualSpent = cat.actual_amount || 0;
      const subItemsHtml = (cat.items || []).map(item => `
        <div class="subitem-row">
          <span>${item.item_name}</span>
          <span>$${item.estimated_cost.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
        </div>
      `).join('');

      card.innerHTML = `
        <div class="cat-header">
          <span class="cat-title">${cat.category}</span>
          <span class="cat-amount">$${cat.allocated_amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
        </div>
        <p class="stat-subtext">${cat.description || ''}</p>
        
        <div style="margin-top:0.75rem; display:flex; align-items:center; justify-content:space-between; gap:0.5rem;">
          <label style="font-size:0.8rem; color:var(--text-dim);">Actual Spend ($):</label>
          <input type="number" class="form-input actual-spend-input" data-index="${idx}" 
                 value="${actualSpent}" step="20" min="0" style="width:120px; padding:0.35rem 0.6rem; font-size:0.85rem;">
        </div>

        <div class="cat-subitems">
          ${subItemsHtml}
        </div>
      `;

      container.appendChild(card);
    });

    // Listen to actual spend edits
    document.querySelectorAll('.actual-spend-input').forEach(input => {
      input.addEventListener('input', (e) => {
        const idx = parseInt(e.target.dataset.index, 10);
        const val = parseFloat(e.target.value) || 0;
        if (state.currentPlan && state.currentPlan.budget_breakdown[idx]) {
          state.currentPlan.budget_breakdown[idx].actual_amount = val;
          updateFinancialMetrics();
        }
      });
    });
  }

  // -------------------------------------------------------------
  // Pillar 2: Milestone Countdown Timeline
  // -------------------------------------------------------------
  function renderMilestoneTimeline(phases) {
    const container = document.getElementById('timeline-container');
    container.innerHTML = '';
    
    let totalTasks = 0;
    let completedTasks = 0;

    phases.forEach((phase, pIdx) => {
      const item = document.createElement('div');
      item.className = 'timeline-item';

      const tasksHtml = (phase.critical_tasks || []).map((task, tIdx) => {
        totalTasks++;
        return `
          <li class="task-item">
            <input type="checkbox" id="task-${pIdx}-${tIdx}" class="task-checkbox">
            <label for="task-${pIdx}-${tIdx}"><span>${task}</span></label>
          </li>
        `;
      }).join('');

      item.innerHTML = `
        <div class="timeline-bullet" aria-hidden="true"></div>
        <div class="timeline-card">
          <div class="timeline-phase">${phase.phase} • Target: ${phase.target_date}</div>
          <div class="timeline-heading">${phase.milestone}</div>
          <ul class="task-checklist">
            ${tasksHtml}
          </ul>
        </div>
      `;
      container.appendChild(item);
    });

    state.milestonesTotal = totalTasks;
    state.milestonesCompleted = completedTasks;
    updateMilestoneProgress();

    // Checkbox toggles
    document.querySelectorAll('.task-checkbox').forEach(cb => {
      cb.addEventListener('change', (e) => {
        const parentLi = e.target.closest('.task-item');
        parentLi.classList.toggle('done', e.target.checked);
        const doneCount = document.querySelectorAll('.task-checkbox:checked').length;
        state.milestonesCompleted = doneCount;
        updateMilestoneProgress();
      });
    });
  }

  function updateMilestoneProgress() {
    const el = document.getElementById('timeline-progress-counter');
    el.textContent = `${state.milestonesCompleted} / ${state.milestonesTotal} Milestones Completed`;
  }

  // -------------------------------------------------------------
  // Pillar 3: Vendor Checklist & RFP Generator
  // -------------------------------------------------------------
  function renderVendorChecklist(vendors) {
    const container = document.getElementById('vendor-container');
    container.innerHTML = '';

    vendors.forEach(v => {
      const card = document.createElement('div');
      card.className = 'vendor-card';

      const questionsList = (v.key_questions_to_ask || []).map(q => `<li>${q}</li>`).join('');

      card.innerHTML = `
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
            <span class="vendor-badge ${v.priority.toLowerCase()}">${v.category}</span>
            <select class="vendor-status-select" data-vendor="${v.id}">
              <option value="Not Contacted" selected>Not Contacted</option>
              <option value="Shortlisted">Shortlisted</option>
              <option value="Contacted">Contacted</option>
              <option value="Proposal Received">Proposal Received</option>
              <option value="Contract Signed">Contract Signed</option>
              <option value="Deposit Paid">Deposit Paid</option>
            </select>
          </div>
          <strong style="font-size:0.98rem; display:block; margin-bottom:0.3rem;">${v.task}</strong>
          <p class="stat-subtext">Booking Window: ${v.recommended_booking_window}</p>
        </div>

        <div class="vendor-questions-box">
          <strong>Key Interview Questions:</strong>
          <ul style="padding-left:1.1rem; line-height:1.5;">${questionsList}</ul>
        </div>

        <button type="button" class="btn btn-secondary btn-sm btn-draft-rfp" data-category="${v.category}">
          ✉️ <span>Draft AI Inquiry Email (RFP)</span>
        </button>
      `;

      container.appendChild(card);
    });

    // RFP Button Clicks
    document.querySelectorAll('.btn-draft-rfp').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const cat = btn.dataset.category;
        openVendorRfpModal(cat);
      });
    });
  }

  async function openVendorRfpModal(vendorCategory) {
    const rfpTextarea = document.getElementById('rfp-email-content');
    rfpTextarea.value = "Synthesizing personalized vendor inquiry with Celebrio AI...";
    modalRfp.classList.add('open');

    try {
      const res = await fetch('/api/vendor-inquiry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vendor_category: vendorCategory,
          event_context: state.currentPlan ? state.currentPlan.event_metadata : {}
        })
      });
      const data = await res.json();
      rfpTextarea.value = data.inquiry_email || "Error generating email.";
    } catch (e) {
      rfpTextarea.value = "Failed to generate inquiry. Please try again.";
    }
  }

  // Copy RFP button
  document.getElementById('btn-copy-rfp').addEventListener('click', () => {
    const text = document.getElementById('rfp-email-content').value;
    navigator.clipboard.writeText(text).then(() => {
      alert("Vendor inquiry email copied to clipboard!");
    });
  });

  document.getElementById('btn-close-rfp-modal').addEventListener('click', () => {
    modalRfp.classList.remove('open');
  });

  // -------------------------------------------------------------
  // Pillar 4: Personalized Ideas Board
  // -------------------------------------------------------------
  function renderPersonalizedIdeas(ideas) {
    document.getElementById('ideas-theme-badge').textContent = ideas.theme_title || "Curated Theme";

    // Palette Swatches
    const palContainer = document.getElementById('palette-container');
    palContainer.innerHTML = '';
    (ideas.color_palette || []).forEach(swatch => {
      const box = document.createElement('div');
      box.className = 'swatch-box';
      box.style.backgroundColor = swatch.hex;
      box.innerHTML = `
        <span class="swatch-name">${swatch.name}</span>
        <span class="swatch-hex">${swatch.hex}</span>
      `;
      box.addEventListener('click', () => {
        navigator.clipboard.writeText(swatch.hex);
        alert(`Copied color ${swatch.hex} (${swatch.name}) to clipboard!`);
      });
      palContainer.appendChild(box);
    });

    // Lists
    populateList('ideas-signature-list', ideas.signature_features || []);
    populateList('ideas-culinary-list', ideas.curated_food_and_drinks || []);
    populateList('ideas-entertainment-list', ideas.entertainment_and_activities || []);

    // Cost-saving tip
    document.getElementById('ideas-cost-saving-tip').textContent = 
      ideas.cost_saving_ai_recommendation || "Optimize catering service style and select in-season florals to maximize budget leverage.";
  }

  function populateList(elementId, items) {
    const el = document.getElementById(elementId);
    el.innerHTML = items.map(item => `<li>${item}</li>`).join('');
  }

  // -------------------------------------------------------------
  // Dashboard Tabs Navigation
  // -------------------------------------------------------------
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const pillar = btn.dataset.pillar;
      
      // Update buttons
      document.querySelectorAll('.tab-btn').forEach(b => {
        const isSelected = b.dataset.pillar === pillar;
        b.classList.toggle('active', isSelected);
        b.setAttribute('aria-selected', isSelected ? 'true' : 'false');
      });

      // Update sections
      document.querySelectorAll('.pillar-content').forEach(p => {
        p.style.display = (p.id === `pillar-${pillar}`) ? 'block' : 'none';
      });
    });
  });

  // -------------------------------------------------------------
  // Live Testing Sandbox Modal
  // -------------------------------------------------------------
  document.getElementById('btn-test-sandbox').addEventListener('click', () => {
    modalTest.classList.add('open');
  });
  document.getElementById('btn-close-test-modal').addEventListener('click', () => {
    modalTest.classList.remove('open');
  });

  document.querySelectorAll('.test-scenario-card').forEach(card => {
    card.addEventListener('click', () => {
      const scenario = card.dataset.scenario;
      modalTest.classList.remove('open');

      if (scenario === 'wedding') {
        initPersona('wedding');
        form.requestSubmit();
      } else if (scenario === 'birthday') {
        initPersona('birthday');
        form.requestSubmit();
      } else if (scenario === 'community') {
        initPersona('community');
        form.requestSubmit();
      } else if (scenario === 'edge-negative') {
        inputBudget.value = -500;
        form.requestSubmit();
      } else if (scenario === 'edge-empty') {
        inputEventName.value = '';
        inputBudget.value = 0;
        form.requestSubmit();
      } else if (scenario === 'edge-xss') {
        inputEventName.value = '<script>alert("Injection")</script> Gala';
        form.requestSubmit();
      }
    });
  });

  // -------------------------------------------------------------
  // Conversational AI Advisor Drawer
  // -------------------------------------------------------------
  document.getElementById('btn-open-chat').addEventListener('click', () => {
    chatDrawer.classList.add('open');
  });
  document.getElementById('btn-close-chat').addEventListener('click', () => {
    chatDrawer.classList.remove('open');
  });

  document.querySelectorAll('.chat-suggestion-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = document.getElementById('chat-input');
      input.value = btn.textContent;
      document.getElementById('chat-form').requestSubmit();
    });
  });

  const chatForm = document.getElementById('chat-form');
  const chatMessages = document.getElementById('chat-messages');

  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    appendChatMessage(msg, 'user');
    input.value = '';

    // Typing bubble
    const typingBubble = appendChatMessage('Celebrio AI is thinking...', 'assistant');

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: msg,
          event_context: state.currentPlan ? state.currentPlan.event_metadata : {
            event_name: inputEventName.value,
            event_type: state.currentPersona,
            budget: parseFloat(inputBudget.value) || 5000,
            guest_count: parseInt(inputGuests.value, 10) || 50
          }
        })
      });

      const data = await res.json();
      typingBubble.remove();
      appendChatMessage(data.reply || "I am currently unable to answer.", 'assistant');
    } catch (e) {
      typingBubble.remove();
      appendChatMessage("Apologies, I encountered an error connecting to the advisor engine.", 'assistant');
    }
  });

  function appendChatMessage(text, role) {
    const div = document.createElement('div');
    div.className = `chat-msg ${role}`;
    // Support markdown newlines and bold
    div.innerHTML = text.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return div;
  }

  // -------------------------------------------------------------
  // Print & Export
  // -------------------------------------------------------------
  document.getElementById('btn-export-print').addEventListener('click', () => {
    window.print();
  });
});
