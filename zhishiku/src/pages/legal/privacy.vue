<template>
  <view class="zk-legal-page">
    <text class="zk-legal-eyebrow">知库 · 个人信息保护说明</text>
    <text class="zk-legal-title">隐私政策</text>
    <text class="zk-legal-meta">更新日期：2026 年 10 月 8 日</text>

    <view class="zk-legal-notice">
      <text class="zk-legal-notice-title">发布前待补充</text>
      <text>运营主体法定名称：[待补充]</text>
      <text>隐私问题联系邮箱或电话：[待补充]</text>
    </view>

    <view class="zk-legal-section">
      <text class="zk-legal-heading">一、我们处理哪些信息</text>
      <text class="zk-legal-paragraph">使用微信快捷登录时，知库调用微信登录能力取得临时登录凭证，并由服务端向微信服务器验证。服务端保存用于识别账号的 OpenID 和知库账号标识；首次登录时生成默认昵称。知库不会通过此流程读取你的微信头像、昵称、手机号或通讯录。</text>
      <text class="zk-legal-paragraph">当你主动上传资料时，服务端接收并保存原文件及解析出的文本，用于在“我的文档”中展示和阅读。个人上传的资料仅对当前账号可见。管理员发布到公开目录的资料会对登录用户开放。</text>
      <text class="zk-legal-paragraph">为保障服务运行和排查故障，服务基础设施可能处理请求时间、网络地址和错误日志等运行信息。</text>
    </view>

    <view class="zk-legal-section">
      <text class="zk-legal-heading">二、信息如何使用和保存</text>
      <text class="zk-legal-paragraph">上述信息用于完成登录、区分账号、保存和展示你主动上传的资料，以及维护服务安全。微信登录凭证只用于服务端向微信验证，不会作为账号密码存储。</text>
      <text class="zk-legal-paragraph">资料保存在知库服务端。你可以在小程序“我的”页面删除个人上传的文档；删除后，服务端会删除对应文档记录和原文件。账号注销、账号信息查询或更正，请使用本页底部公布的联系渠道。</text>
    </view>

    <view class="zk-legal-section">
      <text class="zk-legal-heading">三、信息提供和安全</text>
      <text class="zk-legal-paragraph">知库通过微信提供的小程序登录服务验证登录凭证，并使用服务端基础设施存储和处理资料。除完成上述功能、保障安全或依法依规处理所必需的情况外，知库不会将个人资料用于广告定向或出售给第三方。</text>
      <text class="zk-legal-paragraph">请勿上传你无权处理或不适合在线保存的文件。公开目录中的文档可被所有登录用户阅读，请在发布前确认拥有相应发布和分享权利。</text>
    </view>

    <view class="zk-legal-section">
      <text class="zk-legal-heading">四、未成年人保护</text>
      <text class="zk-legal-paragraph">如你是未成年人，请在监护人指导下使用知库并上传资料。监护人如对未成年人信息处理有疑问，可通过下方联系渠道与运营方联系。</text>
    </view>

    <view class="zk-legal-section">
      <text class="zk-legal-heading">五、联系我们</text>
      <text class="zk-legal-paragraph">运营主体：[待补充法定名称]</text>
      <text class="zk-legal-paragraph">隐私与个人信息保护联系渠道：[待补充邮箱或电话]</text>
    </view>
  </view>
</template>

<script setup lang="ts">
definePageConfig({ navigationBarTitleText: '隐私政策' })
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
