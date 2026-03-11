CREATE DATABASE auth_db;
CREATE DATABASE cases_db;
CREATE DATABASE workflow_db;
CREATE DATABASE images_db;
CREATE DATABASE reports_db;

GRANT ALL PRIVILEGES ON DATABASE auth_db TO pixtral_user;
GRANT ALL PRIVILEGES ON DATABASE cases_db TO pixtral_user;
GRANT ALL PRIVILEGES ON DATABASE workflow_db TO pixtral_user;
GRANT ALL PRIVILEGES ON DATABASE images_db TO pixtral_user;
GRANT ALL PRIVILEGES ON DATABASE reports_db TO pixtral_user;