# 🚀 Groq API Setup Guide for Smart NOC

## ✅ Changes Made

Your Smart NOC system has been configured to use **Groq API** for LLM-powered diagnosis!

### What Changed:
- **Provider:** Ollama (local) → Groq (cloud API)
- **Model:** phi3 → llama-3.1-70b-versatile
- **Speed:** ~180s diagnosis → ~5-10s diagnosis (20x faster!)
- **API Base:** Changed to https://api.groq.com/openai/v1
- **Timeout:** Increased to 60s (Groq is fast, timeout is safety net)

---

## 📝 Setup Steps

### Step 1: Get Your FREE Groq API Key

1. **Visit Groq Console:**
   ```
   https://console.groq.com/keys
   ```

2. **Sign up / Log in:**
   - Use Google, GitHub, or email
   - No credit card required!

3. **Create API Key:**
   - Click "Create API Key"
   - Give it a name: "Smart NOC"
   - Copy the key (starts with `gsk_...`)

---

### Step 2: Update the .env File

Open `.env` file and replace:

```bash
LLM_API_KEY=your_groq_api_key_here
```

With your actual key:

```bash
LLM_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**⚠️ Important:** Keep this key secret! Don't commit it to git.

---

### Step 3: Restart the LLM Diagnosis Service

#### On Windows (PowerShell):
```powershell
cd C:\Users\baisingh\ng-iam\smart-noc
docker compose restart llm-diagnosis
```

#### On Linux/WSL:
```bash
cd /mnt/c/Users/baisingh/ng-iam/smart-noc
docker compose restart llm-diagnosis
```

---

### Step 4: Verify Setup

Check the logs to ensure Groq is working:

```bash
# View logs
docker logs smart-noc-llm-diagnosis --tail 50

# You should see:
# "LLM Client initialized: openai/llama-3.1-70b-versatile"
# "Groq API ready"
```

---

## 🧪 Test Diagnosis

Generate a test incident and watch it get diagnosed in 5-10 seconds:

```bash
# Generate rapid flapping events (creates incident)
cd services/log-generator
python generate_scenarios.py --scenario flapping --count 3 --duration 5

# Wait 10 seconds, then check for diagnosis
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c \
  "SELECT incident_number, 
          LEFT(root_cause, 80) as root_cause, 
          diagnosis_confidence, 
          diagnosed_at 
   FROM incidents 
   WHERE root_cause IS NOT NULL 
   ORDER BY diagnosed_at DESC 
   LIMIT 3;"
```

---

## 📊 Groq Free Tier Limits

```
✅ 30 requests per minute
✅ 14,400 requests per day  
✅ No credit card required
✅ No expiration
```

**For Smart NOC:** This is MORE than enough for development and testing!

---

## 🎛️ Optional: Switch Models

You can use different Groq models by changing `.env`:

### Fast & Lightweight (8B model):
```bash
LLM_MODEL=llama-3.1-8b-instant
```

### Best Quality (70B model - Default):
```bash
LLM_MODEL=llama-3.1-70b-versatile
```

### Alternative (Mixtral):
```bash
LLM_MODEL=mixtral-8x7b-32768
```

See all models: https://console.groq.com/docs/models

---

## 🔧 Troubleshooting

### Error: "Invalid API Key"
- Double-check your API key in `.env`
- Make sure there are no extra spaces
- Restart the service: `docker compose restart llm-diagnosis`

### Error: "Rate limit exceeded"
- You've hit the 30 requests/minute limit
- Wait 1 minute and try again
- Consider adding delay between diagnoses: `DIAGNOSIS_DELAY_SECONDS=10`

### Error: "Connection timeout"
- Check your internet connection
- Groq requires internet access
- Verify firewall isn't blocking api.groq.com

### Service won't start
```bash
# Check logs
docker logs smart-noc-llm-diagnosis

# Restart all services
docker compose restart
```

---

## 🎉 Benefits of Groq

| Feature | Ollama (Before) | Groq (Now) |
|---------|----------------|------------|
| **Speed** | 120-180 seconds | 5-10 seconds |
| **Laptop Impact** | High CPU usage | Zero impact |
| **Model Quality** | Phi-3 (3.8B) | Llama 3.1 (70B) |
| **Cost** | Free (local) | Free (API) |
| **Setup** | Ollama install needed | Just API key |

---

## 🔄 Switch Back to Ollama (If Needed)

If you want to switch back to local Ollama:

```bash
# In .env file:
LLM_MODEL=phi3
LLM_API_KEY=ollama
LLM_API_BASE=http://host.docker.internal:11434/v1
LLM_TIMEOUT=180

# Restart
docker compose restart llm-diagnosis
```

---

## 📚 Additional Resources

- **Groq Console:** https://console.groq.com
- **Groq Docs:** https://console.groq.com/docs
- **Model Comparison:** https://console.groq.com/docs/models
- **Rate Limits:** https://console.groq.com/docs/rate-limits

---

## ✅ Summary

1. Get Groq API key: https://console.groq.com/keys
2. Update `.env` with your key
3. Restart service: `docker compose restart llm-diagnosis`
4. Test with flapping scenario
5. Enjoy 20x faster diagnosis! 🚀

**Need help?** Check the troubleshooting section or Docker logs.
