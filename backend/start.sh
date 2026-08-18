#!/bin/bash
set -e

# 自动检测并填充种子数据（应对Render免费层SQLite不持久的问题）
python -c "
from app import create_app
app = create_app()
with app.app_context():
    from app.models import Brand
    if Brand.query.count() == 0:
        print('[auto-seed] DB empty, seeding...')
        from seed_data import seed_brands, seed_data_sources, seed_mock_articles_lightweight, seed_daily_summaries
        seed_brands()
        seed_data_sources()
        seed_mock_articles_lightweight(days=7)
        seed_daily_summaries()
        print('[auto-seed] Done')
    else:
        print('[auto-seed] DB has data, skip')
" 2>&1

# 启动gunicorn
exec gunicorn \
    -w 2 \
    -b 0.0.0.0:${PORT} \
    --timeout 120 \
    --access-logfile - \
    wsgi:app
