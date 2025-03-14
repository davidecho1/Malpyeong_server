#!/usr/bin/env python
# coding: utf-8

# In[3]:


from AI_API import app
from scheduler import start_scheduler

if __name__ == "__main__":
    # 1) 스케줄러 시작 (매일 0시)
    start_scheduler()

    # 2) Flask API 서버
    app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)


# In[ ]:




