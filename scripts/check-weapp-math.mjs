/** 构建后检查公式引擎、主包容量与分包依赖：node scripts/check-weapp-math.mjs */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
const root = path.resolve('dist')
const app = JSON.parse(fs.readFileSync(path.join(root,'app.json'),'utf8'))
const subRoots = (app.subPackages || []).map((p) => p.root + '/')
const subpackageOf = (file) => subRoots.find((sub) => file.startsWith(sub)) || ''
function files(dir) {
  return fs.readdirSync(dir,{withFileTypes:true}).flatMap((entry) => entry.isDirectory() ? files(path.join(dir,entry.name)) : [path.join(dir,entry.name)])
}
let mainBytes = 0
for (const file of files(root)) {
  const rel = path.relative(root,file).split(path.sep).join('/')
  const pkg = subpackageOf(rel)
  if (!pkg) mainBytes += fs.statSync(file).size
  if (!file.endsWith('.js')) continue
  const source = fs.readFileSync(file,'utf8')
  assert.ok(!source.includes('require("@/'), `未解析的源码路径：${rel}`)
  for (const match of source.matchAll(/require\(["'](\.[^"']+)["']\)/g)) {
    let target = path.resolve(path.dirname(file),match[1])
    if (!path.extname(target)) target += '.js'
    assert.ok(fs.existsSync(target), `缺失依赖：${rel} -> ${match[1]}`)
    const targetPkg = subpackageOf(path.relative(root,target).split(path.sep).join('/'))
    assert.ok(!targetPkg || targetPkg === pkg, `跨分包同步引用：${rel} -> ${match[1]}`)
  }
}
assert.ok(mainBytes < 2*1024*1024, `主包超过 2MB：${mainBytes}`)
assert.ok(fs.existsSync(path.join(root,'katex.js')), '公式引擎未打入共享主包')
assert.ok(fs.readFileSync(path.join(root,'comp.wxss'),'utf8').includes('katex-mini.wxss'), '承载 rich-text 的组件未引入公式样式')
const css = fs.readFileSync(path.join(root,'katex-mini.wxss'),'utf8')
assert.ok(css.includes('data:font/woff2;base64,'), '字体未随包内置')
assert.ok(!/https?:\/\//.test(css), '公式样式仍依赖外部字体')
assert.ok(app.subPackages.find((p) => p.root === 'pages/ziliao').pages.includes('quick-calc'))
console.log(`通过：主包 ${(mainBytes/1024/1024).toFixed(3)}MB；无跨分包同步引用，公式引擎、字体、组件样式及速算路由已打包。`)
