/**
 * BlackRoad OS — Unified Navigation v2
 * Injects consistent nav + journey integration on every page.
 * No emojis. Circles and squares in brand colors.
 */
const blackroadNav = {
  pages: [
    { name: 'Home', url: '/', section: 'main' },
    { name: 'Search', url: '/search.html', section: 'products', panel: 'search', panelUrl: 'https://search.blackroad.io' },
    { name: 'Chat', url: '/chat.html', section: 'products', panel: 'chat', panelUrl: 'https://chat.blackroad.io' },
    { name: 'Agents', url: '/agents-live.html', section: 'products', panel: 'agents', panelUrl: 'https://roundtrip.blackroad.io' },
    { name: 'Status', url: '/status-live.html', section: 'infra', panel: 'status', panelUrl: 'https://blackroad.systems' },
    { name: 'Blog', url: '/blog-index.html', section: 'content' },
    { name: 'Docs', url: '/docs.html', section: 'content' },
    { name: 'Pricing', url: '/pay.html', section: 'business' },
    { name: 'About', url: '/about.html', section: 'main' },
  ],

  secondaryPages: [
    { name: 'Dashboard', url: '/dashboard.html' },
    { name: 'API Docs', url: '/api-docs.html' },
    { name: 'Changelog', url: '/changelog.html' },
    { name: 'Careers', url: '/careers.html' },
    { name: 'Getting Started', url: '/getting-started.html' },
    { name: 'Math', url: '/math.html' },
    { name: 'Roadmap', url: '/roadmap.html' },
    { name: 'Terms', url: '/terms.html' },
    { name: 'Privacy', url: '/privacy.html' },
    { name: 'Contact', url: '/contact.html' },
  ],

  inject(containerId = 'blackroad-nav') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const currentPath = window.location.pathname;
    const isActive = (url) => currentPath === url || (url !== '/' && currentPath.startsWith(url.replace('.html', '')));

    const navLinks = this.pages
      .filter(p => ['main', 'products', 'content', 'business'].includes(p.section))
      .slice(0, 7)
      .map(p => {
        const active = isActive(p.url) ? 'style="opacity:1"' : '';
        if (p.panel && typeof openPanel === 'function') {
          return `<a href="#" onclick="openPanel('${p.panel}','${p.name}','${p.panelUrl}');return false" ${active}>${p.name}</a>`;
        }
        return `<a href="${p.url}" ${active}>${p.name}</a>`;
      }).join('');

    container.innerHTML = `
      <div style="height:4px;background:linear-gradient(90deg,#FF6B2B,#FF2255,#CC00AA,#8844FF,#4488FF,#00D4FF)"></div>
      <nav style="display:flex;align-items:center;justify-content:space-between;padding:0 32px;height:52px;background:rgba(0,0,0,.95);backdrop-filter:blur(16px);border-bottom:1px solid #1a1a1a">
        <a href="/" style="display:flex;align-items:center;gap:10px;text-decoration:none;color:#f5f5f5;font-weight:700;font-size:17px;font-family:'Space Grotesk',sans-serif">
          <span style="display:flex;gap:4px;align-items:center">
            <span style="width:8px;height:8px;border-radius:50%;background:#FF6B2B"></span>
            <span style="width:7px;height:7px;border-radius:1px;background:#FF2255"></span>
            <span style="width:8px;height:8px;border-radius:50%;background:#CC00AA"></span>
            <span style="width:7px;height:7px;border-radius:1px;background:#8844FF"></span>
            <span style="width:8px;height:8px;border-radius:50%;background:#4488FF"></span>
            <span style="width:7px;height:7px;border-radius:1px;background:#00D4FF"></span>
          </span>
          BlackRoad OS
        </a>
        <div class="br-nav-links" style="display:flex;gap:28px">${navLinks}</div>
        <div style="display:flex;gap:10px;align-items:center">
          <span class="br-nav-user" style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#444"></span>
          <a href="https://github.com/BlackRoad-OS-Inc" target="_blank" style="padding:6px 14px;border:1px solid #1a1a1a;border-radius:6px;font-size:12px;font-weight:600;color:#f5f5f5;text-decoration:none;font-family:'Space Grotesk',sans-serif;transition:border-color .2s" onmouseover="this.style.borderColor='#444'" onmouseout="this.style.borderColor='#1a1a1a'">GitHub</a>
        </div>
      </nav>
    `;

    // Style nav links
    const style = document.createElement('style');
    style.textContent = `
      .br-nav-links a{font-size:13px;font-weight:500;color:#f5f5f5;opacity:.45;text-decoration:none;transition:opacity .15s;font-family:'Space Grotesk',sans-serif}
      .br-nav-links a:hover{opacity:1}
      @media(max-width:768px){.br-nav-links{display:none!important}}
    `;
    document.head.appendChild(style);

    // Check auth state
    this.checkAuth();
  },

  checkAuth() {
    const token = localStorage.getItem('blackroad_auth_token');
    const userEl = document.querySelector('.br-nav-user');
    if (token && userEl) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        userEl.textContent = payload.email || payload.user_id || 'signed in';
      } catch(e) {
        userEl.textContent = '';
      }
    }
  }
};

// Auto-inject if container exists on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => blackroadNav.inject());
} else {
  blackroadNav.inject();
}
