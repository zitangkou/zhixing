<template>
  <view class="zk-legal-page">
    <text class="zk-legal-eyebrow">知库 · 服务规则</text>
    <text class="zk-legal-title">用户服务协议</text>
    <text class="zk-legal-meta">更新日期：2026 年 10 月 8 日</text>

    <view class="zk-legal-notice">
      <text class="zk-legal-notice-title">发布前待补充</text>
      <text>运营主体法定名称：[待补充]</text>
      <text>用户服务联系邮箱或电话：[待补充]</text>
    </view>

    <view class="zk-legal-section">
      <text class="zk-legal-heading">一、服务内容</text>
      <text class="zk-legal-paragraph">知库提供知识文档目录浏览、搜索、只读阅读，以及个人资料上传、解析和管理等功能。当前版本通过微信小程序账号登录；登录后，所有用户均可浏览管理员发布的公开目录，暂不提供文档级定向授权或付费权益。</text>
    </view>

    <view class="zk-legal-section">
      <text class="zk-legal-heading">二、账号与资料</text>
      <text class="zk-legal-paragraph">你应通过本人微信账号使用知库，并妥善保管设备和登录状态。你上传资料时，应确保拥有相应的使用和处理权利，不得上传违法违规、侵犯他人权益或危害服务安全的内容。</text>
      <text class="zk-legal-paragraph">个人上传文档仅对本人账号开放。管理员发布的目录内容面向所有登录用户，请不要将其理解为私人或定向分享内容。</text>
    </view>

    <view class="zk-legal-section">
      <text class="zk-legal-heading">三、使用规范与服务调整</text>
      <text class="zk-legal-paragraph">不得利用知库从事违法活动、干扰服务运行、尝试访问他人资料或侵犯第三方合法权益。知库可能因维护、故障或安全原因临时限制部分功能，并会在条件允许时恢复服务。</text>
      <text class="zk-legal-paragraph">阅读页的只读提示和水印用于提醒资料使用范围，不能保证阻止截图、转录或其他客户端行为。请尊重文档权利人的授权和使用要求。</text>
    </view>

    <view class="zk-legal-section">
      <text class="zk-legal-heading">四、联系我们</text>
      <text class="zk-legal-paragraph">运营主体：[待补充法定名称]</text>
      <text class="zk-legal-paragraph">服务联系渠道：[待补充邮箱或电话]</text>
    </view>
  </view>
</template>

<script setup lang="ts">
definePageConfig({ navigationBarTitleText: '用户服务协议' })
</script>

<style lang="scss">
@import '../../styles/tokens.scss';
.zk-legal-page { min-height:100vh; padding:24px 20px 40px; background:$bg; }
.zk-legal-eyebrow,.zk-legal-title,.zk-legal-meta,.zk-legal-heading,.zk-legal-paragraph,.zk-legal-notice text { display:block; }
.zk-legal-eyebrow { color:$brand; font-size:10px; font-weight:700; letter-spacing:1px; }
.zk-legal-title { margin-top:10px; color:$ink; font-size:25px; font-weight:750; }
.zk-legal-meta { margin-top:8px; color:$muted; font-size:10px; }
.zk-legal-notice { margin-top:18px; padding:13px; border:1px solid #edd8a8; border-radius:11px; color:#886b39; background:#fff8e9; font-size:11px; line-height:1.8; }
.zk-legal-notice-title { font-weight:700; }
.zk-legal-section { margin-top:23px; }
.zk-legal-heading { margin-bottom:9px; color:$ink; font-size:14px; font-weight:700; }
.zk-legal-paragraph { margin-top:8px; color:$body; font-size:12px; line-height:1.85; }
</style>
