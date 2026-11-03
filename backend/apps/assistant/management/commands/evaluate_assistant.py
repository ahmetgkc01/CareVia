import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.assistant.evaluation import (
    evaluate_assistant,
    evaluate_retrieval,
    evaluate_safety,
    load_eval_cases,
)


class Command(BaseCommand):
    help = "Evaluate Carevia assistant safety, retrieval, grounding proxy, latency, and cost."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset",
            default=str(settings.BASE_DIR / "apps" / "assistant" / "evals" / "cases.json"),
        )
        parser.add_argument(
            "--username",
            default="",
            help="Run end-to-end assistant cases as this existing synthetic user.",
        )
        parser.add_argument("--output", default="", help="Optional JSON report path.")

    def handle(self, *args, **options):
        dataset_path = Path(options["dataset"])
        if not dataset_path.is_file():
            raise CommandError(f"Eval dataset not found: {dataset_path}")
        try:
            cases = load_eval_cases(dataset_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise CommandError(str(exc)) from exc

        report = {
            "dataset": str(dataset_path),
            "safety": evaluate_safety(cases),
            "retrieval": evaluate_retrieval(cases),
        }
        if options["username"]:
            User = get_user_model()
            try:
                user = User.objects.get(username=options["username"])
            except User.DoesNotExist as exc:
                raise CommandError("The requested eval user does not exist.") from exc
            report["assistant"] = evaluate_assistant(cases, user)
        else:
            report["assistant"] = {
                "skipped": "Pass --username to run groundedness, latency, token, and cost cases."
            }

        rendered = json.dumps(report, ensure_ascii=False, indent=2)
        self.stdout.write(rendered)
        if options["output"]:
            output_path = Path(options["output"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered + "\n", encoding="utf-8")
