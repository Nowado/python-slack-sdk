import json
import logging
from logging import Logger
from typing import Optional

from botocore.client import BaseClient

from slack_sdk.oauth.installation_store.async_installation_store import (
    AsyncInstallationStore,
)
from slack_sdk.oauth.installation_store.installation_store import InstallationStore
from slack_sdk.oauth.installation_store.models.bot import Bot
from slack_sdk.oauth.installation_store.models.installation import Installation


class AmazonS3InstallationStore(InstallationStore, AsyncInstallationStore):
    def __init__(
        self,
        *,
        s3_client: BaseClient,
        bucket_name: str,
        client_id: str,
        historical_data_enabled: bool = True,
        logger: Logger = logging.getLogger(__name__),
    ):
        self.s3_client = s3_client
        self.bucket_name = bucket_name
        self.historical_data_enabled = historical_data_enabled
        self.client_id = client_id
        self._logger = logger

    @property
    def logger(self) -> Logger:
        if self._logger is None:
            self._logger = logging.getLogger(__name__)
        return self._logger

    async def async_save(self, installation: Installation):
        return self.save(installation)

    def save(self, installation: Installation):
        none = "none"
        e_id = installation.enterprise_id or none
        t_id = installation.team_id or none
        workspace_path = f"{self.client_id}/{e_id}-{t_id}"

        if self.historical_data_enabled:
            history_version: str = str(installation.installed_at)
            entity: str = json.dumps(installation.to_bot().__dict__)
            response = self.s3_client.put_object(
                Bucket=self.bucket_name,
                Body=entity,
                Key=f"{workspace_path}/bot-latest",
            )
            self.logger.debug(f"S3 put_object response: {response}")
            response = self.s3_client.put_object(
                Bucket=self.bucket_name,
                Body=entity,
                Key=f"{workspace_path}/bot-{history_version}",
            )
            self.logger.debug(f"S3 put_object response: {response}")

            u_id = installation.user_id or none
            entity: str = json.dumps(installation.__dict__)
            response = self.s3_client.put_object(
                Bucket=self.bucket_name,
                Body=entity,
                Key=f"{workspace_path}/installer-{u_id}-latest",
            )
            self.logger.debug(f"S3 put_object response: {response}")
            response = self.s3_client.put_object(
                Bucket=self.bucket_name,
                Body=entity,
                Key=f"{workspace_path}/installer-{u_id}-{history_version}",
            )
            self.logger.debug(f"S3 put_object response: {response}")

        else:
            entity: str = json.dumps(installation.to_bot().__dict__)
            response = self.s3_client.put_object(
                Bucket=self.bucket_name,
                Body=entity,
                Key=f"{workspace_path}/bot-latest",
            )
            self.logger.debug(f"S3 put_object response: {response}")

            u_id = installation.user_id or none
            entity: str = json.dumps(installation.__dict__)
            response = self.s3_client.put_object(
                Bucket=self.bucket_name,
                Body=entity,
                Key=f"{workspace_path}/installer-{u_id}-latest",
            )
            self.logger.debug(f"S3 put_object response: {response}")

    async def async_find_bot(
        self, *, enterprise_id: Optional[str], team_id: Optional[str],
    ) -> Optional[Bot]:
        return self.find_bot(enterprise_id=enterprise_id, team_id=team_id)

    def find_bot(
        self, *, enterprise_id: Optional[str], team_id: Optional[str],
    ) -> Optional[Bot]:
        # Not yet implemented: org-apps support
        none = "none"
        e_id = enterprise_id or none
        t_id = team_id or none
        workspace_path = f"{self.client_id}/{e_id}-{t_id}"
        try:
            fetch_response = self.s3_client.get_object(
                Bucket=self.bucket_name, Key=f"{workspace_path}/bot-latest",
            )
            self.logger.debug(f"S3 get_object response: {fetch_response}")
            body = fetch_response["Body"].read().decode("utf-8")
            data = json.loads(body)
            return Bot(**data)
        except Exception as e:  # skipcq: PYL-W0703
            message = f"Failed to find bot installation data for enterprise: {e_id}, team: {t_id}: {e}"
            self.logger.warning(message)
            return None
