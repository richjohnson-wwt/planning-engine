# Render.com Deployment - Quick Start Guide

## 🚀 Quick Deploy (5 minutes)

### Step 1: Push to GitHub
```bash
git add .
git commit -m "Add Render deployment configuration"
git push origin main
```

### Step 2: Deploy on Render
1. Go to [render.com](https://render.com) and login
2. Click **"New"** → **"Blueprint"**
3. Connect your GitHub repository: `planning-engine`
4. Render will detect `render.yaml` automatically
5. Click **"Apply"** to create both services

### Step 3: Update Frontend API URL
After the API service is deployed:
1. Copy your API URL (e.g., `https://planning-engine-api.onrender.com`)
2. Go to the **Web service** settings in Render
3. Navigate to **Environment** tab
4. Update `VITE_API_URL` to your actual API URL
5. Click **"Save Changes"** and trigger a manual deploy

### Step 4: Test Your Deployment
- **API**: Visit `https://planning-engine-api.onrender.com/docs`
- **Web**: Visit `https://planning-engine-web.onrender.com`

---

## 🤖 GitHub Actions Auto-Deploy Setup

### Get Required Information

1. **Render API Key**:
   - Render Dashboard → Account Settings → API Keys
   - Create new key and copy it

2. **Service IDs**:
   - Go to each service's page
   - Copy the Service ID from the URL or Settings
   - Example: `srv-xxxxxxxxxxxxxxxxxxxxx`

### Add GitHub Secrets

1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions
3. Add these secrets:
   - `RENDER_API_KEY`: Your Render API key
   - `RENDER_API_SERVICE_ID`: API service ID
   - `RENDER_WEB_SERVICE_ID`: Web service ID

### How to Find Service IDs

**Method 1 - From URL:**
When viewing a service, the URL looks like:
```
https://dashboard.render.com/web/srv-xxxxxxxxxxxxxxxxxxxxx
                                    ^^^^^^^^^^^^^^^^^^^^^^^^
                                    This is your Service ID
```

**Method 2 - From Settings:**
1. Click on your service
2. Go to "Settings"
3. Scroll to "Service Details"
4. Copy the "Service ID"

### Test Auto-Deploy

```bash
# Make any change and push to main
git add .
git commit -m "Test auto-deploy"
git push origin main
```

Watch the deployment in:
- GitHub: Actions tab
- Render: Dashboard (both services will deploy)

---

## 📋 What Was Created

### Configuration Files
- ✅ `render.yaml` - Render Blueprint configuration
- ✅ `requirements.txt` - Python dependencies
- ✅ `.github/workflows/deploy.yml` - GitHub Actions workflow
- ✅ `apps/web/.env.production` - Production environment config
- ✅ Updated `apps/web/src/services/api.js` - Dynamic API URL

### Services Created
1. **planning-engine-api** (Web Service)
   - Python FastAPI backend
   - Auto-deploys from main branch
   - Health check at `/docs`

2. **planning-engine-web** (Static Site)
   - Vue.js frontend
   - Auto-deploys from main branch
   - Serves from `apps/web/dist`

---

## ⚠️ Important Notes

### Free Tier Behavior
- Services **spin down after 15 minutes** of inactivity
- First request after spin-down takes **30-60 seconds**
- This is normal for Render's free tier

### API URL Configuration
The frontend needs to know where the backend is:
- **Local dev**: Uses proxy (`/api` → `localhost:8000`)
- **Production**: Uses `VITE_API_URL` environment variable

**You MUST update `VITE_API_URL` after deploying the API!**

### CORS (if needed)
If you encounter CORS errors, add this to `apps/api/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://planning-engine-web.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🔧 Troubleshooting

### Build Fails
- Check build logs in Render Dashboard
- Verify all dependencies are in `requirements.txt` and `package.json`
- Ensure Python 3.13+ compatibility

### Frontend Can't Connect to API
1. Verify `VITE_API_URL` is set correctly
2. Check API service is running (not spun down)
3. Test API directly: `https://your-api-url.onrender.com/docs`
4. Check browser console for errors

### GitHub Actions Fails
- Verify all 3 secrets are added correctly
- Check Service IDs are correct (start with `srv-`)
- Review workflow run logs in GitHub Actions tab

### Service Won't Start
- Check environment variables are set
- Review service logs in Render Dashboard
- Verify start command is correct

---

## 📚 Full Documentation

For complete details, see [`DEPLOYMENT.md`](./DEPLOYMENT.md)

---

## 🎯 Next Steps

1. ✅ Deploy to Render using Blueprint
2. ✅ Update `VITE_API_URL` in web service
3. ✅ Set up GitHub Actions secrets
4. ✅ Test the full application
5. 🎉 Start using your deployed VRPTW system!

---

## 💡 Tips

- **Monitor logs**: Keep an eye on logs during first deployment
- **Test locally first**: Always test changes locally before deploying
- **Use manual deploy**: You can manually trigger deploys from Render Dashboard
- **Check status**: Render shows build/deploy status in real-time
- **Upgrade later**: Consider paid plans for production use (no spin-down)

---

## 🆘 Need Help?

- **Render Issues**: [Render Documentation](https://render.com/docs)
- **GitHub Actions**: Check workflow logs in Actions tab
- **Application Errors**: Review service logs in Render Dashboard
