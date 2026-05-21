#!/bin/bash
# ============================================================================
# 港力工程 — AI Agent Server 啟動 Script
# 
# 用法:
#   bash start_server.sh
#
# 事前準備:
#   1. export DEEPSEEK_API_KEY="sk-xxxxxxxx" (必需)
#   2. 改 server.py TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID
# ============================================================================

cd "$(dirname "$0")"

echo "🦾 港力工程 AI Server v2.0"
echo "=============================="
echo ""

# Check API key
if [ -z "$DEEPSEEK_API_KEY" ]; then
  echo "⚠️  DEEPSEEK_API_KEY 未設定！AI agent 會離線。"
  echo "   請執行: export DEEPSEEK_API_KEY=\"sk-xxxxxxxx\""
  echo ""
fi

echo "→ Agents: QuoteBot | SaveCalc | BookMate | HelpBot | RankUp | PostGen"
echo "→ Port:   http://localhost:8520"
echo "→ Health: http://localhost:8520/health"
echo ""
echo "按 Ctrl+C 停止"
echo ""

python server.py
