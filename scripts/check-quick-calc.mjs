/** 数学正确性与场景约束验证：node scripts/check-quick-calc.mjs */
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { build } from 'esbuild'
async function importTs(path) {
  const result = await build({ entryPoints: [path], bundle: true, platform: 'node', format: 'esm', write: false })
  return import('data:text/javascript;base64,' + Buffer.from(result.outputFiles[0].text).toString('base64'))
}
const { QUICK_METHODS, generateQuickSession } = await importTs('src/utils/quickCalc.ts')
const { splitMathText, normalizeLatex } = await importTs('src/utils/mathText.ts')
const { renderMiniLatex } = await importTs('src/utils/latexMini.ts')
let seed = 473892
const rng = () => { seed = (Math.imul(seed,1664525)+1013904223) >>> 0; return seed / 2**32 }
let checked = 0
const answerPositions = new Set()
const comparisons = new Set()
for (const mode of ['mixed', ...QUICK_METHODS.map((m) => m.id)]) {
  for (let batch = 0; batch < 50; batch++) {
    const questions = generateQuickSession(mode, 20, rng)
    assert.equal(questions.length,20)
    assert.equal(new Set(questions.map((q) => q.latex)).size,20)
    if (mode === 'mixed') assert.equal(new Set(questions.map((q) => q.method)).size,QUICK_METHODS.length)
    for (const q of questions) {
      checked++
      assert.equal(q.options.length,4)
      assert.equal(new Set(q.options).size,4)
      assert.ok(q.answer >= 0 && q.answer < 4)
      answerPositions.add(q.answer)
      assert.ok(renderMiniLatex(q.latex,true,'#1a1a1a').length)
      for (const step of q.steps) if (step.latex) assert.ok(renderMiniLatex(step.latex,true,'#e4e4e6').length)
      if (q.check.kind === 'compare') {
        const [a,b,c,d] = q.check.values
        assert.ok([a,b,c,d].every((v) => Number.isSafeInteger(v) && v > 0))
        const sign = Math.sign(a*d-c*b)
        comparisons.add(sign)
        const expected = sign > 0 ? '>' : sign < 0 ? '<' : '='
        assert.equal(q.options[q.answer], expected)
        if (q.method === 'direct') assert.ok((a>c && b<d)||(a<c && b>d))
        const [largeN,largeD,smallN,smallD] = a>c ? [a,b,c,d] : [c,d,a,b]
        if (q.method === 'difference') {
          assert.ok(largeD>smallD)
          assert.ok(largeN-smallN < smallN && largeD-smallD < smallD)
          // 差分数与较小分子分母的原分数的关系，与两个原分数的关系一致。
          assert.equal(Math.sign((largeN-smallN)*smallD-smallN*(largeD-smallD)),Math.sign(largeN*smallD-smallN*largeD))
        }
        if (q.method === 'position') {
          assert.ok([2,3,4].some((k) => largeN>k*smallN && largeD<k*smallD))
        }
        if (q.method === 'split') {
          assert.ok(a<b && c<d)
          assert.ok((a>c && b-a<d-c)||(a<c && b-a>d-c))
          assert.equal(Math.sign(a*(d-c)-c*(b-a)),sign)
        }
      } else {
        const { values, target, unit } = q.check
        const distances = values.map((v) => Math.abs(v-target))
        assert.equal(distances.filter((v) => v === 0).length,1)
        assert.equal(distances[q.answer],0)
        assert.equal(Number(q.options[q.answer].replace(unit || ' ','')), target)
        // 从展示表达式独立计算，防止生成器内部 target 与真正公式偏离。
        const numbers = q.plain.match(/\d+(?:\.\d+)?/g).map(Number)
        if (q.method === 'growth-amount') assert.equal(Math.round(numbers[0]*numbers[1]/(100+numbers[1])),target)
        if (q.method === 'growth-rate') assert.equal(Math.round((numbers[0]-numbers[1])/numbers[2]*1000)/10,target)
        if (q.method === 'base') assert.equal(Math.round(numbers[0]/(1+numbers[2]/100)),target)
      }
    }
  }
}
assert.equal(answerPositions.size,4)
assert.deepEqual([...comparisons].sort(),[-1,1])
assert.equal(normalizeLatex('$$\\frac{1}{2}$$'),'\\frac{1}{2}')
for (const text of ['普通正文', '未闭合 $x', String.raw`费用 \$20`, '$$未闭合']) {
  assert.equal(splitMathText(text).filter((s) => s.type === 'formula').length,0)
}
const segments = splitMathText('公式 $x^2$，块公式 $$\\frac{1}{2}$$\n```latex\nx+1\n```')
assert.equal(segments.filter((s) => s.type === 'formula').length,3)
assert.equal(segments.filter((s) => s.display).length,2)
const radical = JSON.stringify(renderMiniLatex(String.raw`\sqrt{x^2+1}`,true,'#e4e4e6'))
assert.ok(radical.includes('e4e4e6'))
assert.throws(() => renderMiniLatex(String.raw`\notARealCommand{`,true,'#1a1a1a'))
const python = process.platform === 'win32' ? 'server/.venv/Scripts/python.exe' : 'server/.venv/bin/python'
const serverCheck = spawnSync(python, ['server/scripts/check_quick_calc.py'], { encoding: 'utf8' })
if (serverCheck.stdout) process.stdout.write(serverCheck.stdout)
if (serverCheck.stderr) process.stderr.write(serverCheck.stderr)
assert.equal(serverCheck.status, 0, '服务端速算题生成校验失败')
console.log(`通过：${checked} 道题的答案、场景约束、选项与公式渲染；分隔符和暗色根号校验。`)
