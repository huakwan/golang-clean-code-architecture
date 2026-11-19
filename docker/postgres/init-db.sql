SELECT 'CREATE DATABASE django_clean_arch'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'django_clean_arch')\gexec
