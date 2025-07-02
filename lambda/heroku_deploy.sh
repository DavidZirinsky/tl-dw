#!/bin/bash

# 1. Login to Heroku
heroku login

# 2. Create a new Heroku app (replace 'tldw' with your desired name)
heroku create tldw

# 3. Set the stack to container (for docker deployment)
heroku stack:set container -a tldw

# 4. Set your OpenAI API key as an environment variable
heroku config:set OPENAI_API_KEY=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 -a tldw

# 5. Add git remote for heroku (if not already added by heroku create)
heroku git:remote -a tl-dw

# 6. Deploy your application
git add .
git commit -m "Deploy to Heroku"
git push heroku main

# 7. Check logs if needed
heroku logs --tail -a tldw

# 8. Open your app
heroku open -a tldw