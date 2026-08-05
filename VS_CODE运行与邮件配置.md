# VS Code运行与邮件配置

## 1. 在macOS启动

在VS Code中打开项目文件夹，然后在Terminal依次运行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
```

编辑`.env`，完成邮件配置后运行：

```bash
python3 app.py
```

浏览器打开`http://127.0.0.1:5000`。

## 2. Gmail发送验证码

`.env`需要填写：

```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=你的Gmail地址
MAIL_PASSWORD=Google生成的16位App Password
MAIL_DEFAULT_SENDER=你的Gmail地址
ALLOWED_EMAIL_DOMAIN=columbia.edu
```

`MAIL_PASSWORD`不能填写普通Gmail登录密码。需要先为Google账户开启两步验证，然后创建App Password。

## 3. 邮件功能

- 注册成功后向Columbia邮箱发送6位验证码。
- 验证码只以哈希形式保存在`users.db`。
- 验证码10分钟后失效。
- Verify页面支持重新发送验证码。
- Forgot Password向已验证账户发送6位密码重置验证码。
- 新密码必须至少8个字符，并包含大写字母、小写字母和数字。

## 4. 安全提醒

- 不要把填写真实密码后的`.env`提交或发送给其他人。
- 对外部署时应设置新的长随机`SECRET_KEY`。
- HTTPS部署后，把`SESSION_COOKIE_SECURE`设为`True`。
- `users.db`包含账户信息，分享项目时应确认接收对象有权访问。

