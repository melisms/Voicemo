
from pathlib import Path

from huggingface_hub import snapshot_download


class ModelManager:
    REPO_ID = "melisms/voicemo-emotion2vec"
    REVISION = "d830254a5d75641cefc30ca64d6b149d3624835e"

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = (
            cache_dir
            or Path.home() / ".cache" / "voicemo" / "models"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_emotion2vec_model_path(self) -> Path:
        """
        Download the model snapshot if necessary and return
        its local directory.

        Hugging Face caches downloaded files, so subsequent
        calls reuse the existing snapshot.
        """
        model_path = Path(
            snapshot_download(
                repo_id=self.REPO_ID,
                cache_dir=str(self.cache_dir),
                revision=self.REVISION,
            )
        )

        required_files = [
            "model.pt",
            "config.yaml",
            "configuration.json",
            "tokens.txt",
        ]

        missing_files = [
            filename
            for filename in required_files
            if not (model_path / filename).is_file()
        ]

        if missing_files:
            raise FileNotFoundError(
                "Incomplete emotion2vec model. Missing files: "
                + ", ".join(missing_files)
            )

        return model_path
