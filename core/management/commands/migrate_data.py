from django.core.management.base import BaseCommand
from django.db import connection
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Migrate data from old core_* tables to new app-specific tables'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            self.stdout.write('Starting data migration...')
            
            # Disable foreign key constraints temporarily
            cursor.execute("PRAGMA foreign_keys = OFF;")
            
            # First, we need to get the first user as default created_by for projects
            default_user_id = User.objects.first().id if User.objects.exists() else None
            if not default_user_id:
                self.stdout.write(self.style.ERROR('No users found! Please create a user first.'))
                return
            
            # Migrate Project data
            self.stdout.write('Migrating Project data...')
            cursor.execute("""
                INSERT INTO projects_project (id, name, description, created_by_id, created_at, updated_at)
                SELECT id, name, description, %s, created_at, updated_at
                FROM core_project
                WHERE NOT EXISTS (
                    SELECT 1 FROM projects_project WHERE projects_project.id = core_project.id
                )
            """, [default_user_id])
            
            # Migrate Tag data
            self.stdout.write('Migrating Tag data...')
            cursor.execute("""
                INSERT INTO testing_tag (id, name, color, project_id, created_at)
                SELECT id, name, color, project_id, COALESCE(created_at, datetime('now'))
                FROM core_tag
                WHERE NOT EXISTS (
                    SELECT 1 FROM testing_tag WHERE testing_tag.id = core_tag.id
                )
            """)
            
            # Migrate Test data (mapping old structure to new)
            self.stdout.write('Migrating Test data...')
            cursor.execute("""
                INSERT INTO testing_test (id, title, file_path, line, column, test_id, story, project_id, created_at, comment)
                SELECT id, title, file_path, line, column, test_id, story, project_id, created_at, comment
                FROM core_test
                WHERE NOT EXISTS (
                    SELECT 1 FROM testing_test WHERE testing_test.id = core_test.id
                )
            """)
            
            # Migrate TestExecution data (mapping old structure to new)
            self.stdout.write('Migrating TestExecution data...')
            cursor.execute("""
                INSERT INTO testing_testexecution (
                    id, project_id, config_file, root_dir, playwright_version, workers, actual_workers,
                    git_commit_hash, git_commit_short_hash, git_branch, git_commit_subject, 
                    git_author_name, git_author_email, ci_build_href, ci_commit_href,
                    start_time, duration, expected_tests, skipped_tests, unexpected_tests, flaky_tests,
                    created_at, comment, raw_json
                )
                SELECT 
                    id, project_id, config_file, root_dir, playwright_version, workers, actual_workers,
                    git_commit_hash, git_commit_short_hash, git_branch, git_commit_subject,
                    git_author_name, git_author_email, ci_build_href, ci_commit_href,
                    start_time, duration, expected_tests, skipped_tests, unexpected_tests, flaky_tests,
                    created_at, comment, raw_json
                FROM core_testexecution
                WHERE NOT EXISTS (
                    SELECT 1 FROM testing_testexecution WHERE testing_testexecution.id = core_testexecution.id
                )
            """)
            
            # Migrate TestResult data (mapping old structure to new)
            self.stdout.write('Migrating TestResult data...')
            cursor.execute("""
                INSERT INTO testing_testresult (
                    id, execution_id, test_id, project_id, project_name, timeout, expected_status, status,
                    worker_index, parallel_index, duration, retry, start_time,
                    errors, stdout, stderr, steps, annotations, attachments
                )
                SELECT 
                    id, execution_id, test_id, project_id, project_name, timeout, expected_status, status,
                    worker_index, parallel_index, duration, retry, start_time,
                    COALESCE(errors, '[]'), COALESCE(stdout, '[]'), COALESCE(stderr, '[]'), 
                    COALESCE(steps, '[]'), COALESCE(annotations, '[]'), COALESCE(attachments, '[]')
                FROM core_testresult
                WHERE NOT EXISTS (
                    SELECT 1 FROM testing_testresult WHERE testing_testresult.id = core_testresult.id
                )
            """)
            
            # Migrate many-to-many relationships for Test-Tag (if table exists)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='core_test_tags'")
            if cursor.fetchone():
                self.stdout.write('Migrating Test-Tag relationships...')
                cursor.execute("""
                    INSERT INTO testing_test_tags (id, test_id, tag_id)
                    SELECT id, test_id, tag_id
                    FROM core_test_tags
                    WHERE NOT EXISTS (
                        SELECT 1 FROM testing_test_tags WHERE testing_test_tags.id = core_test_tags.id
                    )
                """)
            
            # Migrate API Key data (mapping old structure to new)
            self.stdout.write('Migrating APIKey data...')
            cursor.execute("""
                INSERT INTO api_apikey (id, name, key, can_upload, can_read, created_at, last_used, is_active, expires_at, user_id)
                SELECT id, name, key, can_upload, can_read, created_at, last_used, is_active, expires_at, user_id
                FROM core_apikey
                WHERE NOT EXISTS (
                    SELECT 1 FROM api_apikey WHERE api_apikey.id = core_apikey.id
                )
            """)
            
            # Note: CI Configuration tables don't exist in old schema, skipping them
            self.stdout.write('Note: No CI configuration tables found in old schema - skipping...')
            
            # Re-enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON;")
            
            self.stdout.write(self.style.SUCCESS('Data migration completed successfully!'))