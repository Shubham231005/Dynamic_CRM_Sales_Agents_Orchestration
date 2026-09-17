import React, { useState, useEffect } from 'react';
import { api } from './api';
import { Search, User, MessageCircle, Phone, Instagram, Send, Bell, UserPlus, Inbox, Settings, Paperclip } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState('generate'); // generate, leads, inbox
  
  // States
  const [industry, setIndustry] = useState('');
  const [location, setLocation] = useState('');
  const [requirement, setRequirement] = useState('');
  const [salesContext, setSalesContext] = useState('');
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  
  // Settings State
  const [settings, setSettings] = useState({
    email_address: '', email_password: '',
    phone_number: '', twilio_account_sid: '', twilio_auth_token: '', bland_api_key: '',
    instagram_username: '', instagram_password: '',
    telegram_bot_token: '', telegram_chat_id: ''
  });

  // Notifications / Inbox
  const [inbox, setInbox] = useState([]);

  useEffect(() => {
    if (activeTab === 'leads') {
      fetchLeads();
    }
    if (activeTab === 'settings') {
      fetchSettings();
    }
  }, [activeTab]);

  const fetchLeads = async () => {
    setLoading(true);
    try {
      const res = await api.getLeads();
      setLeads(res || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const fetchSettings = async () => {
    try {
      const data = await api.getSettings();
      setSettings(data);
    } catch(e) { console.error(e); }
  };

  const saveSettings = async (e) => {
    e.preventDefault();
    try {
      await api.updateSettings(settings);
      alert('Credentials saved successfully!');
    } catch(e) {
      alert('Failed to save settings');
    }
  };

  const handleFindLeads = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const searchIndustry = industry.trim() || 'Dental Clinics';
      const searchLocation = location.trim() || 'Mumbai';
      
      const res = await fetch(`http://${window.location.hostname}:8000/api/leads/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ industry: searchIndustry, location: searchLocation, max_results: 10, provider: 'google_maps' })
      });
      const data = await res.json();
      if (data.success && data.total_found > 0) {
        alert(`Agents found ${data.total_found} leads!`);
        setActiveTab('leads');
      } else {
        alert(`No new leads found (found ${data.total_found || 0} total, ${data.duplicates || 0} duplicates).`);
        setActiveTab('leads');
      }
    } catch (e) {
      alert("Error finding leads: " + e.message);
    }
    setLoading(false);
  };

  const handleStrategizeLead = async (leadId) => {
    setActionLoading(`strategize-${leadId}`);
    try {
      await api.strategizeLead(leadId, salesContext);
      await fetchLeads();
      alert('Lead Scored & Playbook Generated!');
    } catch(e) {
      alert('Failed to score lead. Make sure GROQ_API_KEY is in backend .env');
    }
    setActionLoading(null);
  };

  const handleDelegateAction = async (lead, actionName) => {
    setActionLoading(`outreach-${lead.id}-${actionName}`);
    try {
      const channelMap = {
        'Call': 'call',
        'WhatsApp': 'whatsapp',
        'Email': 'email',
        'Insta DM': 'instagram',
        'Telegram': 'telegram'
      };
      
      const channel = channelMap[actionName];
      if (!channel) {
        alert('Unknown channel.');
        return;
      }
      
      const data = await api.executeOutreach(lead.id, channel);
      if (data.success) {
        alert(`Success! Agent says: ${data.message}`);
      } else {
        alert(`Failed: ${data.detail}`);
      }
    } catch(e) {
      alert(`Error executing outreach. Check if backend is running and credentials are set.`);
    }
    setActionLoading(null);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (file.name.toLowerCase().endsWith('.pdf')) {
      const formData = new FormData();
      formData.append('file', file);
      try {
        const res = await fetch(`http://${window.location.hostname}:8000/api/strategy/parse-pdf`, {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (data.success) {
          setSalesContext(prev => prev ? prev + '\n\n--- PDF Attached ---\n' + data.text : data.text);
          alert('PDF parsed successfully!');
        } else {
          alert('Failed to parse PDF: ' + (data.detail || 'Unknown error'));
        }
      } catch (err) {
        alert('Failed to upload PDF. Check if PyPDF2 and python-multipart are installed.');
      }
      return;
    }

    const reader = new FileReader();
    reader.onload = (evt) => {
      const text = evt.target.result;
      setSalesContext(prev => prev ? prev + '\n\n--- Document Attached ---\n' + text : text);
      alert('Document attached and parsed into the Sales Context!');
    };
    reader.onerror = () => {
      alert('Error reading the file. Please use a text-based format or PDF.');
    };
    reader.readAsText(file);
  };

  const handleInboxAction = (id, action) => {
    setInbox(inbox.filter(i => i.id !== id));
    alert(`Agent instructed: ${action}. They will execute the follow-up now.`);
  };

  return (
    <div className="mobile-crm-container">
      {/* HEADER */}
      <header className="mobile-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div className="avatar">
            <User size={20} color="#fff" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.2rem', margin: 0 }}>Sales Copilot</h1>
            <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Welcome back, Alex</p>
          </div>
        </div>
        <Bell size={24} color="var(--text-secondary)" />
      </header>

      <main className="mobile-main">
        {/* TAB 1: GENERATE LEADS */}
        {activeTab === 'generate' && (
          <div className="fade-in">
            <div className="card">
              <h2 className="card-title">What are we selling today?</h2>
              <p className="item-subtitle" style={{ marginBottom: '1.5rem' }}>Tell your AI Agents who to look for, and they will hunt down quality leads.</p>
              
              <form onSubmit={handleFindLeads}>
                <div style={{ marginBottom: '1rem' }}>
                  <label className="input-label">Target Industry</label>
                  <input 
                    type="text" 
                    placeholder="e.g. Healthcare, Supermarkets, SaaS" 
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    required
                  />
                </div>
                <div style={{ marginBottom: '1rem' }}>
                  <label className="input-label">Target Location</label>
                  <input 
                    type="text" 
                    placeholder="e.g. Mumbai, New York" 
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    required
                  />
                </div>
                <div style={{ marginBottom: '1.5rem' }}>
                  <label className="input-label">Our Requirement / Pitch</label>
                  <textarea 
                    placeholder="Describe what you want the agents to sell..." 
                    rows={3}
                    style={{ width: '100%', backgroundColor: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)', color: '#fff', padding: '0.75rem', borderRadius: '0.5rem', fontFamily: 'inherit' }}
                    value={requirement}
                    onChange={(e) => setRequirement(e.target.value)}
                  />
                </div>

                <div style={{ marginBottom: '1.5rem' }}>
                  <label className="input-label" style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Sales Context (For LLM)</span>
                    <label style={{ cursor: 'pointer', color: 'var(--primary-color)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                      <Paperclip size={14} /> Attach Document / PDF
                      <input type="file" accept=".txt,.md,.csv,.json,.pdf" style={{ display: 'none' }} onChange={handleFileUpload} />
                    </label>
                  </label>
                  <textarea 
                    placeholder="Paste example outreach emails, strict guidelines, or click 'Attach Document' to load a file..." 
                    rows={4}
                    style={{ width: '100%', backgroundColor: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)', color: '#fff', padding: '0.75rem', borderRadius: '0.5rem', fontFamily: 'inherit' }}
                    value={salesContext}
                    onChange={(e) => setSalesContext(e.target.value)}
                  />
                </div>
                
                <button type="submit" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
                  {loading ? <span className="loader"></span> : <Search size={18} />}
                  Find Quality Leads
                </button>
              </form>
            </div>
          </div>
        )}

        {/* TAB 2: MY LEADS */}
        {activeTab === 'leads' && (
          <div className="fade-in">
            <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>Leads Found by Agents</h2>
            {loading ? (
              <div style={{ textAlign: 'center', padding: '2rem' }}><div className="loader"></div></div>
            ) : leads.length === 0 ? (
              <p className="item-subtitle">No leads yet. Go find some!</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {leads.map(lead => (
                  <div key={lead.id} className="card" style={{ padding: '1.25rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{lead.company_name}</h3>
                        <p className="item-subtitle">{lead.industry} • {lead.location}</p>
                      </div>
                      
                      {lead.strategic_fit ? (
                        <div style={{ textAlign: 'right' }}>
                          <span className="badge success">Score: {Math.round(lead.strategic_fit.fit_score * 100)}%</span>
                        </div>
                      ) : (
                        <button 
                          className="outline" 
                          style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                          onClick={() => handleStrategizeLead(lead.id)}
                          disabled={actionLoading === `strategize-${lead.id}`}
                        >
                          {actionLoading === `strategize-${lead.id}` ? 'Scoring...' : 'Get Score Card'}
                        </button>
                      )}
                    </div>
                    
                    {lead.strategic_fit && (
                      <div style={{ marginTop: '0.75rem', padding: '0.75rem', backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: '0.5rem' }}>
                        <p style={{ fontSize: '0.85rem', color: '#cbd5e1' }}><strong>AI Analysis:</strong> {lead.strategic_fit.reasoning}</p>
                      </div>
                    )}
                    
                    <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
                      <p style={{ fontSize: '0.85rem', marginBottom: '0.75rem', color: 'var(--text-secondary)' }}>Tell Agent to reach out via:</p>
                      <div className="action-buttons-grid">
                        <button className="action-btn" onClick={() => handleDelegateAction(lead, 'Call')} disabled={actionLoading === `outreach-${lead.id}-Call`}>
                          <Phone size={16} /> {actionLoading === `outreach-${lead.id}-Call` ? 'Executing...' : 'Call'}
                        </button>
                        <button className="action-btn" onClick={() => handleDelegateAction(lead, 'WhatsApp')} style={{ backgroundColor: '#059669' }} disabled={actionLoading === `outreach-${lead.id}-WhatsApp`}>
                          <MessageCircle size={16} /> {actionLoading === `outreach-${lead.id}-WhatsApp` ? 'Executing...' : 'WhatsApp'}
                        </button>
                        <button className="action-btn" onClick={() => handleDelegateAction(lead, 'Email')} style={{ backgroundColor: '#2563eb' }} disabled={actionLoading === `outreach-${lead.id}-Email`}>
                          <Send size={16} /> {actionLoading === `outreach-${lead.id}-Email` ? 'Executing...' : 'Email'}
                        </button>
                        <button className="action-btn" onClick={() => handleDelegateAction(lead, 'Insta DM')} style={{ background: 'linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%)' }} disabled={actionLoading === `outreach-${lead.id}-Insta DM`}>
                          <Instagram size={16} /> {actionLoading === `outreach-${lead.id}-Insta DM` ? 'Executing...' : 'Insta DM'}
                        </button>
                        <button className="action-btn" onClick={() => handleDelegateAction(lead, 'Telegram')} style={{ backgroundColor: '#0088cc' }} disabled={actionLoading === `outreach-${lead.id}-Telegram`}>
                          <Send size={16} /> {actionLoading === `outreach-${lead.id}-Telegram` ? 'Executing...' : 'Telegram'}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 3: AGENT INBOX */}
        {activeTab === 'inbox' && (
          <div className="fade-in">
            <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>Updates from Agents</h2>
            {inbox.length === 0 ? (
              <p className="item-subtitle">Agents are working. No updates right now.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {inbox.map(msg => (
                  <div key={msg.id} className="card" style={{ borderLeft: '4px solid var(--danger)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                      <div className="agent-avatar"><BrainCircuit size={14} color="#fff" /></div>
                      <span style={{ fontSize: '0.85rem', fontWeight: '600' }}>AI Sales Agent</span>
                    </div>
                    <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>Re: {msg.lead}</h3>
                    <p style={{ fontSize: '0.9rem', marginBottom: '1rem', color: '#e2e8f0', backgroundColor: 'rgba(0,0,0,0.3)', padding: '0.75rem', borderRadius: '0.5rem' }}>
                      "{msg.message}"
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      <button className="action-btn full-width outline" onClick={() => handleInboxAction(msg.id, 'Try WhatsApp instead')}>
                        <MessageCircle size={16} /> Tell Agent: Try WhatsApp instead
                      </button>
                      <button className="action-btn full-width outline" onClick={() => handleInboxAction(msg.id, 'Offer a 10% discount')}>
                        <Send size={16} /> Tell Agent: Offer a 10% discount
                      </button>
                      <button className="action-btn full-width danger" onClick={() => handleInboxAction(msg.id, 'Drop lead')}>
                        Drop lead
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 4: SETTINGS */}
        {activeTab === 'settings' && (
          <div className="fade-in">
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                <Settings color="var(--primary-color)" size={24} />
                <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Agent Credentials</h2>
              </div>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>Provide the credentials below so the AI agents can physically execute outreach via these channels.</p>
              
              <form onSubmit={saveSettings}>
                <h3 style={{ fontSize: '1rem', marginBottom: '1rem', color: 'var(--primary-color)' }}>Email Setup</h3>
                <div style={{ marginBottom: '1rem' }}>
                  <label className="input-label">Gmail / SMTP Email Address</label>
                  <input type="email" style={{ width: '100%', padding: '0.5rem', borderRadius: '0.25rem' }} value={settings.email_address || ''} onChange={e => setSettings({...settings, email_address: e.target.value})} placeholder="you@company.com" />
                </div>
                <div style={{ marginBottom: '1.5rem' }}>
                  <label className="input-label">App Password</label>
                  <input type="password" style={{ width: '100%', padding: '0.5rem', borderRadius: '0.25rem' }} value={settings.email_password || ''} onChange={e => setSettings({...settings, email_password: e.target.value})} placeholder="16-digit App Password" />
                </div>

                <h3 style={{ fontSize: '1rem', marginBottom: '1rem', color: '#25D366' }}>Phone / WhatsApp (Twilio)</h3>
                <div style={{ marginBottom: '1rem' }}>
                  <label className="input-label">Twilio Phone Number</label>
                  <input type="text" style={{ width: '100%', padding: '0.5rem', borderRadius: '0.25rem' }} value={settings.phone_number || ''} onChange={e => setSettings({...settings, phone_number: e.target.value})} placeholder="+1234567890" />
                </div>
                <div style={{ marginBottom: '1rem' }}>
                  <label className="input-label">Twilio Account SID</label>
                  <input type="text" style={{ width: '100%', padding: '0.5rem', borderRadius: '0.25rem' }} value={settings.twilio_account_sid || ''} onChange={e => setSettings({...settings, twilio_account_sid: e.target.value})} placeholder="AC..." />
                </div>
                <div style={{ marginBottom: '1.5rem' }}>
                  <label className="input-label">Twilio Auth Token</label>
                  <input type="password" style={{ width: '100%', padding: '0.5rem', borderRadius: '0.25rem' }} value={settings.twilio_auth_token || ''} onChange={e => setSettings({...settings, twilio_auth_token: e.target.value})} placeholder="Secret Token" />
                </div>

                <h3 style={{ fontSize: '1rem', marginBottom: '1rem', color: '#E1306C' }}>Instagram Automation</h3>
                <div style={{ marginBottom: '1rem' }}>
                  <label className="input-label">Instagram Username</label>
                  <input type="text" style={{ width: '100%', padding: '0.5rem', borderRadius: '0.25rem' }} value={settings.instagram_username || ''} onChange={e => setSettings({...settings, instagram_username: e.target.value})} placeholder="@your_handle" />
                </div>
                <div style={{ marginBottom: '1.5rem' }}>
                  <label className="input-label">Instagram Password</label>
                  <input type="password" style={{ width: '100%', padding: '0.5rem', borderRadius: '0.25rem' }} value={settings.instagram_password || ''} onChange={e => setSettings({...settings, instagram_password: e.target.value})} placeholder="Password" />
                </div>

                <h3 style={{ fontSize: '1rem', marginBottom: '1rem', color: '#0088cc' }}>Telegram Bot</h3>
                <div style={{ marginBottom: '1rem' }}>
                  <label className="input-label">Bot Token</label>
                  <input type="text" style={{ width: '100%', padding: '0.5rem', borderRadius: '0.25rem' }} value={settings.telegram_bot_token || ''} onChange={e => setSettings({...settings, telegram_bot_token: e.target.value})} placeholder="BotFather Token" />
                </div>
                <div style={{ marginBottom: '1.5rem' }}>
                  <label className="input-label">Chat ID</label>
                  <input type="text" style={{ width: '100%', padding: '0.5rem', borderRadius: '0.25rem' }} value={settings.telegram_chat_id || ''} onChange={e => setSettings({...settings, telegram_chat_id: e.target.value})} placeholder="Chat ID" />
                </div>

                <button type="submit" style={{ width: '100%', justifyContent: 'center', marginTop: '1rem' }}>
                  Save Credentials
                </button>
              </form>
            </div>
          </div>
        )}
      </main>

      {/* BOTTOM NAVIGATION */}
      <nav className="bottom-nav">
        <div className={`nav-item ${activeTab === 'generate' ? 'active' : ''}`} onClick={() => setActiveTab('generate')}>
          <UserPlus size={24} />
          <span>Find Leads</span>
        </div>
        <div className={`nav-item ${activeTab === 'leads' ? 'active' : ''}`} onClick={() => setActiveTab('leads')}>
          <Search size={24} />
          <span>My Leads</span>
        </div>
        <div className={`nav-item ${activeTab === 'inbox' ? 'active' : ''}`} onClick={() => setActiveTab('inbox')}>
          <div style={{ position: 'relative' }}>
            <Inbox size={24} />
            {inbox.length > 0 && <span className="notification-dot"></span>}
          </div>
          <span>Updates</span>
        </div>
        <div className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`} onClick={() => setActiveTab('settings')}>
          <Settings size={24} />
          <span>Settings</span>
        </div>
      </nav>
    </div>
  );
}

export default App;
