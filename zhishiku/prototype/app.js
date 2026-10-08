const docs = [
  { id: 'ai-research', title: 'AI 时代的知识工作流', category: 'AI', format: 'MD', type: '深度专题', author: '知库研究组', time: '12 分钟', views: '2.4k', thumb: 'thumb-ai', symbol: '知' },
  { id: 'business-notes', title: '从 0 到 1：商业模式画布', category: '商业', format: 'PDF', type: '案例拆解', author: '商业观察室', time: '9 分钟', views: '1.8k', thumb: 'thumb-business', symbol: '策' },
  { id: 'design-system', title: '设计系统：从规范到协作', category: '设计', format: 'MD', type: '实战手册', author: '产品设计组', time: '15 分钟', views: '1.2k', thumb: 'thumb-design', symbol: '形' },
  { id: 'research-method', title: '高效研究的 7 个方法', category: 'AI', format: 'DOCX', type: '研究方法', author: '知库研究组', time: '7 分钟', views: '986', thumb: 'thumb-research', symbol: '研' },
]
const titles = { 'ai-research': 'AI 时代的知识工作流', 'business-notes': '从 0 到 1：商业模式画布', 'design-system': '设计系统：从规范到协作', 'research-method': '高效研究的 7 个方法', 'learning-system': '搭建个人学习系统' }
let activeFilter = '全部'
let toastTimer

function renderDocs() {
  const visible = docs.filter((doc) => activeFilter === '全部' || doc.category === activeFilter)
  document.querySelector('#doc-list').innerHTML = visible.map((doc) => `
    <article class="doc-row" data-doc="${doc.id}">
      <div class="doc-thumb ${doc.thumb}">${doc.symbol}</div>
      <div class="doc-copy"><span class="doc-type"><b>${doc.format}</b> ${doc.type}</span><h3>${doc.title}</h3>
        <div class="doc-meta"><span>${doc.author}</span><span>·</span><span>${doc.time}</span><span class="access-pill">${doc.format === 'MD' ? '定向可读' : '会员专享'}</span></div></div>
      <button class="row-more" aria-label="更多">···</button>
    </article>`).join('')
}
renderDocs()

function showToast(message) {
  let toast = document.querySelector('.toast')
  if (!toast) {
    toast = document.createElement('div')
    toast.className = 'toast'
    document.body.appendChild(toast)
  }
  toast.textContent = message
  toast.classList.add('visible')
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => toast.classList.remove('visible'), 2100)
}

function openSheet(content) {
  document.querySelector('#sheet-content').innerHTML = content
  const overlay = document.querySelector('#overlay')
  overlay.classList.add('open')
  overlay.setAttribute('aria-hidden', 'false')
}
function closeSheet() {
  document.querySelector('#overlay').classList.remove('open')
  document.querySelector('#overlay').setAttribute('aria-hidden', 'true')
}
function changePage(name) {
  document.querySelectorAll('.page').forEach((page) => page.classList.toggle('active', page.id === `${name}-page`))
  document.querySelectorAll('.tab').forEach((tab) => tab.classList.toggle('active', tab.dataset.page === name))
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function articleFor(id) {
  const doc = docs.find((item) => item.id === id)
  const title = titles[id] || '搭建个人学习系统'
  const format = doc?.format || (id === 'learning-system' ? 'PDF' : 'MD')
  return `<span class="eyebrow">READING ROOM · 安全阅读</span><h2>${title}</h2>
    <div class="sheet-title-meta"><span>${format}</span><span>·</span><span>${doc?.author || '知库精选'}</span><span>·</span><span>${doc?.time || '8 分钟'}</span></div>
    <div class="reader" oncopy="return false" oncontextmenu="return false" onselectstart="return false">
      <h3>让知识从收藏，真正走向复用</h3><p>我们每天接触大量信息，但真正留下来的内容并不多。问题往往不在于输入太少，而在于知识没有形成可以持续调用的结构。</p>
      <h4>01 · 建立轻量的捕获入口</h4><p>把灵感、文章和项目材料先放入统一的收集箱。记录时补充一句「为什么值得留下」，让未来的自己能快速找回当时的判断。</p>
      <div class="reader-callout">好的知识管理，不是把更多东西存起来，而是让重要的东西更容易再次被找到。</div>
      <h4>02 · 用主题连接信息</h4><p>围绕正在解决的问题组织材料，用标签和双向链接呈现内容之间的关系。每次阅读后留下一条自己的注释，把别人的观点转化为自己的理解。</p>
      <ul><li>捕获：低摩擦记录，避免遗漏</li><li>整理：按主题聚合，建立上下文</li><li>复用：在写作与决策中重新调用</li></ul>
      <h4>03 · 让 AI 成为思考伙伴</h4><p>把可靠的资料交给 AI 提取结构、比较观点和生成问题。最终结论仍由你判断，来源与原文始终可以追溯。</p>
    </div>
    <div class="reader-actions"><button class="secondary-action" data-action="bookmark">☆ 收藏</button><button class="secondary-action" data-action="share">↗ 定向分享</button><button class="primary-action" data-action="ask-ai">✳ AI 解读</button></div>
    <p style="font-size:8px;margin:10px 0 0;color:#afb1b6">阅读权限：仅限本人 · 页面含专属水印 · 禁止复制与转发原文</p>`
}

function openArticle(id) { openSheet(articleFor(id)) }
function openShare() {
  openSheet(`<span class="eyebrow">CONTROLLED ACCESS</span><h2>定向分享</h2><p>把资料分享给指定的人，并随时管理访问权限。</p>
    <div class="permission-list"><div class="permission-row"><span>♙</span><div><b>指定成员可见</b><small>仅受邀账号可打开文档</small></div><strong>已开启</strong></div>
    <div class="permission-row"><span>◷</span><div><b>有效期</b><small>到期后自动关闭访问</small></div><strong>7 天</strong></div>
    <div class="permission-row"><span>▤</span><div><b>阅读保护</b><small>只读 · 动态水印 · 禁止复制</small></div><strong>已开启</strong></div></div>
    <div class="share-link"><span>zhiku.app/s/8Kp2mQ · 仅受邀成员可访问</span><button data-action="copy-link">复制链接</button></div>
    <div class="permission-note">分享链接本身不代表访问授权。访问者还需通过账号校验；服务端会检查成员名单、有效期与访问次数。</div>
    <button class="primary-action" style="width:100%" data-action="invite">＋ 选择成员并创建分享</button>`)
}
function openPermissions() {
  openSheet(`<span class="eyebrow">READING PROTECTION</span><h2>阅读权限</h2><p>针对不同资料设置访问与阅读保护规则。</p>
    <div class="toggle-row"><span>只读模式</span><button class="toggle on" data-toggle aria-label="切换只读模式"></button></div>
    <div class="toggle-row"><span>动态身份水印</span><button class="toggle on" data-toggle aria-label="切换动态身份水印"></button></div>
    <div class="toggle-row"><span>禁止复制与文本选择</span><button class="toggle on" data-toggle aria-label="切换禁止复制"></button></div>
    <div class="toggle-row"><span>访问时效校验</span><button class="toggle on" data-toggle aria-label="切换访问时效"></button></div>
    <div class="permission-note">客户端可以减少普通复制操作；内容授权必须由服务端执行。截图、拍照无法由小程序彻底阻止，建议使用用户身份水印和访问审计降低泄露风险。</div>
    <button class="primary-action" style="width:100%" data-action="save-permissions">保存设置</button>`)
}
function openFeature(action) {
  const screens = {
    favorites: ['我的收藏', '收藏的文档会保存在这里，方便你随时继续阅读。', '♡'],
    history: ['最近阅读', '查看最近打开的资料和阅读进度。', '◷'],
    shares: ['我的分享', '你创建的定向分享会显示在这里，可以撤销访问、延长有效期或调整成员。', '↗'],
    downloads: ['离线资料', '已缓存 3 份资料，可在无网络时阅读。', '⇩'],
    privacy: ['隐私与安全', '管理登录设备、账号保护和阅读记录。', '♧'],
    appearance: ['外观与阅读', '个性化你的阅读体验。', '◐'],
    notifications: ['消息通知', '内容更新、分享动态和重要安全提醒。', '♢'],
    about: ['关于知库', '知库是一款面向知识工作者的安全阅读与知识管理工具。', '知'],
    membership: ['知库会员', '解锁专属知识专题、AI 深度解读与更灵活的分享管理。', '✳'],
    all: ['全部文档', '正在为你整理更多精选知识。', '知'],
    refresh: ['猜你喜欢', '推荐内容已为你更新。', '↻'],
    'ask-ai': ['AI 文档解读', '我已准备好从核心观点、结构脉络和可执行建议三个角度解读这份资料。接入真实 AI 服务后，可以针对全文继续追问。', '✳'],
    invite: ['选择成员', '选择已有知库成员，或输入受邀者的绑定手机号/账号。被邀请者登录后才能打开资料。', '♙'],
  }
  const [title, desc, icon] = screens[action] || ['知库设置', '该功能入口已就绪。', '知']
  openSheet(`<span class="eyebrow">ZHI-KU · PERSONAL SPACE</span><h2>${title}</h2><p style="margin-top:11px">${desc}</p><div class="permission-note">产品演示原型 · 数据为示例内容</div><button class="primary-action" style="width:100%" data-action="close">完成</button>`)
}

document.addEventListener('click', (event) => {
  const target = event.target.closest('[data-page], [data-doc], [data-filter], [data-action], [data-toggle]')
  if (!target) return
  if (target.dataset.page) { changePage(target.dataset.page); return }
  if (target.dataset.filter) {
    activeFilter = target.dataset.filter
    document.querySelectorAll('.chip').forEach((chip) => chip.classList.toggle('active', chip.dataset.filter === activeFilter))
    renderDocs(); return
  }
  if (target.dataset.doc) { openArticle(target.dataset.doc); return }
  if (target.hasAttribute('data-toggle')) { target.classList.toggle('on'); return }
  const action = target.dataset.action
  if (!action) return
  if (action === 'close') closeSheet()
  else if (action === 'share') openShare()
  else if (action === 'permissions') openPermissions()
  else if (action === 'copy-link') {
    const link = 'https://zhiku.app/s/8Kp2mQ'
    if (navigator.clipboard?.writeText) navigator.clipboard.writeText(link).catch(() => {})
    showToast('分享链接已复制')
    return
  }
  else if (action === 'save-permissions') { closeSheet(); showToast('阅读权限已保存'); return }
  else if (action === 'bookmark') { target.textContent = target.textContent.includes('已收藏') ? '☆ 收藏' : '✓ 已收藏'; showToast('已加入我的收藏'); return }
  else openFeature(action)
})

document.querySelector('#overlay').addEventListener('click', (event) => { if (event.target.id === 'overlay') closeSheet() })
document.querySelector('#search-input').addEventListener('input', (event) => {
  const query = event.target.value.trim().toLowerCase()
  const results = document.querySelector('#search-results')
  if (!query) { results.innerHTML = ''; return }
  const matches = docs.filter((doc) => `${doc.title} ${doc.category} ${doc.type} ${doc.author}`.toLowerCase().includes(query))
  results.innerHTML = matches.length ? matches.slice(0, 4).map((doc) => `<div class="search-hit" data-doc="${doc.id}"><b>${doc.format}</b> ${doc.title}<span>›</span></div>`).join('') : '<div class="search-hit">没有找到相关文档<span>试试其他关键词</span></div>'
})
document.addEventListener('copy', (event) => {
  if (!window.getSelection()?.anchorNode?.parentElement?.closest('.reader')) return
  event.preventDefault()
  showToast('该文档仅供只读，请勿复制')
})
document.addEventListener('contextmenu', (event) => {
  if (event.target.closest('.reader')) event.preventDefault()
})
document.addEventListener('keydown', (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); document.querySelector('#search-input').focus() }
  if (event.key === 'Escape') closeSheet()
})
