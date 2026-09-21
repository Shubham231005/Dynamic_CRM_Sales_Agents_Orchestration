const API_BASE = `http://${window.location.hostname}:8000/api`;

export const api = {
  // Leads
  getLeads: async () => {
    const res = await fetch(`${API_BASE}/leads?limit=200`);
    return res.json();
  },
  
  // Strategy
  strategizeLead: async (leadId, salesContext = "") => {
    const res = await fetch(`${API_BASE}/strategy/leads/${leadId}/strategize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sales_context: salesContext })
    });
    return res.json();
  },

  orchestrateBatch: async (leadIds, salesContext = "") => {
    const res = await fetch(`${API_BASE}/strategy/orchestrate-batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lead_ids: leadIds, sales_context: salesContext })
    });
    return res.json();
  },
  
  // Approvals
  getApprovals: async () => {
    const res = await fetch(`${API_BASE}/strategy/approvals`);
    return res.json();
  },
  
  decideApproval: async (id, decision) => {
    const res = await fetch(`${API_BASE}/strategy/approvals/${id}/decide?decision=${decision}`, {
      method: 'POST'
    });
    return res.json();
  },

  // Settings
  getSettings: async () => {
    const res = await fetch(`${API_BASE}/settings`);
    return res.json();
  },

  updateSettings: async (settingsData) => {
    const res = await fetch(`${API_BASE}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settingsData)
    });
    return res.json();
  },

  // Execute Outreach
  executeOutreach: async (leadId, channel) => {
    const res = await fetch(`${API_BASE}/outreach/execute/${leadId}/${channel}`, {
      method: 'POST'
    });
    return res.json();
  },
  
  // Playbooks
  getPlaybooks: async () => {
    const res = await fetch(`${API_BASE}/strategy/playbooks`);
    return res.json();
  },
  
  createPlaybook: async (data) => {
    const res = await fetch(`${API_BASE}/strategy/playbooks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return res.json();
  }
};
