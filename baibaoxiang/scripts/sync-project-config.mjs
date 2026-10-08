import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const projectDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const envPath = path.join(projectDir, '.env')
const configPath = path.join(projectDir, 'project.config.json')

if (!fs.existsSync(envPath)) {
  throw new Error('缺少 baibaoxiang/.env，请先配置 APP_ID。')
}

const envLines = fs.readFileSync(envPath, 'utf8').split(/\r?\n/)
const appIdLine = envLines.find((line) => /^\s*(?:export\s+)?APP_ID\s*=/.test(line))
const appId = appIdLine?.replace(/^\s*(?:export\s+)?APP_ID\s*=\s*/, '').trim().replace(/^(['"])(.*)\1$/, '$2')

if (!appId) {
  throw new Error('baibaoxiang/.env 中的 APP_ID 为空，请先填写小程序 AppID。')
}

const config = JSON.parse(fs.readFileSync(configPath, 'utf8'))
config.appid = appId
fs.writeFileSync(configPath, `${JSON.stringify(config, null, 2)}\n`)
console.log('已从本地 .env 同步小程序 AppID 到 project.config.json。')
