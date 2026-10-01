import os
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from psycopg import sql

VALID_ROLE = re.compile(r"^[a-z][a-z0-9_]{2,62}$")


class Command(BaseCommand):
    help = "Create or rotate a least-privilege PostgreSQL runtime role for Carevia."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="carevia_app")

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("This command requires PostgreSQL.")

        username = options["username"]
        if not VALID_ROLE.fullmatch(username):
            raise CommandError("The runtime username contains unsupported characters.")

        password = os.getenv("CAREVIA_RUNTIME_DB_PASSWORD", "")
        if len(password) < 32:
            raise CommandError(
                "CAREVIA_RUNTIME_DB_PASSWORD must contain at least 32 characters."
            )

        database_name = connection.settings_dict["NAME"]
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication "
                "FROM pg_roles WHERE rolname = %s",
                [username],
            )
            role_attributes = cursor.fetchone()
            role_exists = role_attributes is not None
            password_literal = sql.Literal(password)
            role_identifier = sql.Identifier(username)

            if role_exists:
                if any(role_attributes):
                    raise CommandError(
                        "Refusing to rotate a runtime role with elevated privileges."
                    )
                cursor.execute(
                    sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(
                        role_identifier, password_literal
                    )
                )
            else:
                cursor.execute(
                    sql.SQL(
                        "CREATE ROLE {} WITH LOGIN PASSWORD {} "
                        "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION"
                    ).format(role_identifier, password_literal)
                )

            cursor.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(database_name), role_identifier
                )
            )
            cursor.execute(
                sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role_identifier)
            )
            cursor.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES "
                    "IN SCHEMA public TO {}"
                ).format(role_identifier)
            )
            cursor.execute(
                sql.SQL(
                    "GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES "
                    "IN SCHEMA public TO {}"
                ).format(role_identifier)
            )
            cursor.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}"
                ).format(role_identifier)
            )
            cursor.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                    "GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {}"
                ).format(role_identifier)
            )

        action = "rotated" if role_exists else "created"
        self.stdout.write(self.style.SUCCESS(f"Runtime database role {username} {action}."))
