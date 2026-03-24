/**
 * BlackRoad OS — Crosslinks v2
 * 1. "Keep Exploring" contextual suggestions before footer
 * 2. Cross-domain SEO link bar after footer
 */
(function(){
  // ── Keep Exploring ──
  var LINKS = {
    products: [
      {title:'Search',sub:'AI-powered answers',href:'#',panel:'search',url:'https://search.blackroad.io'},
      {title:'Chat',sub:'200 agents with memory',href:'#',panel:'chat',url:'https://chat.blackroad.io'},
      {title:'Agents',sub:'Browse the full roster',href:'#',panel:'agents',url:'https://roundtrip.blackroad.io'},
      {title:'Fleet Status',sub:'Live hardware monitoring',href:'#',panel:'status',url:'https://blackroad.systems'},
    ],
    content: [
      {title:'Blog',sub:'Technical writing',href:'/blog-index.html'},
      {title:'Docs',sub:'API reference',href:'/docs.html'},
      {title:'How It Works',sub:'Animated infographics',href:'/infographics.html'},
      {title:'Changelog',sub:'What shipped',href:'/changelog.html'},
    ],
    business: [
      {title:'Pricing',sub:'Free to $20/mo',href:'/pay.html'},
      {title:'Careers',sub:'Join the road',href:'/careers.html'},
      {title:'About',sub:'The story',href:'/about.html'},
    ],
    blog: [
      {title:'Quit Finance',sub:'Series 7 to Raspberry Pis',href:'/blog-quit-finance.html'},
      {title:'Sovereign OS',sub:'Full cost breakdown',href:'/blog-sovereign-os-150.html'},
      {title:'200 Agents',sub:'One Worker, 200 personas',href:'/blog-200-agents.html'},
      {title:'Amundson Sequence',sub:'Number theory',href:'/blog-amundson-sequence.html'},
    ]
  };

  var path = window.location.pathname;
  var sections = [];
  if (path.includes('blog')) sections = ['products','content'];
  else if (path.includes('doc') || path.includes('api')) sections = ['products','blog'];
  else if (path.includes('pay') || path.includes('enterprise')) sections = ['products','content'];
  else if (path.includes('agent') || path.includes('chat') || path.includes('search')) sections = ['blog','content'];
  else sections = ['products','blog','content'];

  var links = [];
  sections.forEach(function(s) {
    (LINKS[s]||[]).forEach(function(l) {
      if (l.href !== path && l.href !== path.replace('.html','')) links.push(l);
    });
  });
  links = links.slice(0,6);

  if (links.length > 0) {
    var html = '<div style="max-width:1100px;margin:0 auto;padding:40px 48px 20px;border-top:1px solid #1a1a1a">';
    html += '<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:#444;letter-spacing:.1em;text-transform:uppercase;margin-bottom:16px">Keep Exploring</div>';
    html += '<div style="display:flex;gap:12px;overflow-x:auto;padding-bottom:8px;-webkit-overflow-scrolling:touch">';
    links.forEach(function(l) {
      var click = '';
      if (l.panel && typeof openPanel === 'function') {
        click = 'onclick="openPanel(\''+l.panel+'\',\''+l.title+'\',\''+l.url+'\');return false"';
      }
      html += '<a href="'+l.href+'" '+click+' style="min-width:160px;max-width:200px;border:1px solid #1a1a1a;border-radius:8px;padding:14px 18px;text-decoration:none;color:#f5f5f5;transition:border-color .2s;flex-shrink:0" onmouseover="this.style.borderColor=\'#333\'" onmouseout="this.style.borderColor=\'#1a1a1a\'">';
      html += '<div style="font-size:13px;font-weight:600;margin-bottom:2px;font-family:\'Space Grotesk\',sans-serif">'+l.title+'</div>';
      html += '<div style="font-family:\'Inter\',sans-serif;font-size:11px;color:#737373">'+l.sub+'</div>';
      html += '</a>';
    });
    html += '</div></div>';

    var footer = document.querySelector('footer');
    if (footer) footer.insertAdjacentHTML('beforebegin', html);
    else document.body.insertAdjacentHTML('beforeend', html);
  }

  // ── Cross-domain SEO bar ──
  if(document.getElementById('br-crosslinks')) return;
  var domains = [
    ['blackroad.io','Home'],['search.blackroad.io','Search'],['chat.blackroad.io','Chat'],
    ['roundtrip.blackroad.io','Agents'],['social.blackroad.io','Social'],
    ['blackroad.systems','Status'],['blackroadai.com','AI'],
    ['lucidia.earth','Lucidia'],['roadchain.io','Blockchain'],
    ['pay.blackroad.io','Pricing'],['brand.blackroad.io','Brand'],
    ['github.com/BlackRoad-OS-Inc','GitHub']
  ];
  var host = location.hostname;
  var domainHtml = domains.filter(function(l){ return !host.includes(l[0].split('.')[0]); }).map(function(l){
    return '<a href="https://'+l[0]+'" style="color:#333;text-decoration:none;font-size:0.6rem;transition:color 0.2s" onmouseover="this.style.color=\'#888\'" onmouseout="this.style.color=\'#333\'">'+l[1]+'</a>';
  }).join(' · ');
  var d = document.createElement('div');
  d.id = 'br-crosslinks';
  d.style.cssText = 'text-align:center;padding:8px 16px;font-family:"JetBrains Mono",monospace;border-top:1px solid #111;background:#050505;';
  d.innerHTML = domainHtml;
  var ft = document.querySelector('footer');
  if(ft) ft.parentNode.insertBefore(d, ft.nextSibling);
  else document.body.appendChild(d);
})();
