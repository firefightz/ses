In Python (and most environments), the order of precedence for environment variables is:
Explicitly set environment variables in the process (e.g., from Terraform, export VAR=value, or your CI/CD pipeline).
Variables loaded from a .env file (via python-dotenv or similar).
So if both exist for the same variable:
# .env
DB_HOST=localhost
# Terraform / CI
DB_HOST=rds.production.example.com
Python code running with os.environ["DB_HOST"] will see rds.production.example.com — the one set in the environment before the .env file is loaded.
Loading the .env file with load_dotenv() does not overwrite existing environment variables by default.