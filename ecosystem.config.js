// pm2 ecosystem.config.js
// 로그인(scripts/login.py)은 1회성 대화형 스크립트라 pm2 대상에서 제외합니다.
// interpreter가 venv를 쓰는 경우 아래 경로를 venv의 python3로 바꿔주세요
// (예: "./venv/bin/python3").
module.exports = {
  apps: [
    {
      name: "raffle-registrar",
      script: "scripts/registrar.py",
      interpreter: "python3",
      cwd: __dirname,
      autorestart: true,
      max_restarts: 20,
      restart_delay: 3000,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
    {
      name: "raffle-scheduler",
      script: "scripts/scheduler.py",
      interpreter: "python3",
      cwd: __dirname,
      autorestart: true,
      max_restarts: 20,
      restart_delay: 3000,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
  ],
};
