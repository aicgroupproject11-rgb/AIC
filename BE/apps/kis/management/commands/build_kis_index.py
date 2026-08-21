import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from search_engine.builder import BuildOptions, build_search_index


class Command(BaseCommand):
    help = "Build the hybrid domain/BoW/R-tree KIS search index"

    def add_arguments(self, parser):
        parser.add_argument("--data-root", type=Path, default=settings.KIS_DATA_ROOT)
        parser.add_argument("--manifest", type=Path)
        parser.add_argument("--index-dir", type=Path, default=settings.KIS_INDEX_ROOT)
        parser.add_argument("--pca-dim", type=int, default=24)
        parser.add_argument("--object-min-score", type=float, default=0.25)

    def handle(self, *args, **options):
        try:
            metadata = build_search_index(
                data_root=options["data_root"],
                manifest_path=options["manifest"],
                index_dir=options["index_dir"],
                options=BuildOptions(
                    pca_dimensions=options["pca_dim"],
                    object_min_score=options["object_min_score"],
                ),
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(json.dumps(metadata, ensure_ascii=False, indent=2)))
