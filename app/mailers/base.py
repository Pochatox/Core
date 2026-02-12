from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Generic, Self, TypeVar

import aiosmtplib

from app.mailers.configs import BaseMailerConfig, SMTPConfig


class MailerError(Exception): ...
class NonExistentEmail(MailerError): ...


MailerConfig = TypeVar('MailerConfig', bound=BaseMailerConfig)


@dataclass
class BaseAsyncMailer(ABC, Generic[MailerConfig]):
    config: MailerConfig

    @abstractmethod
    async def connect(self) -> Self: ...

    @abstractmethod
    async def send(self, subject: str, body: str,
                   to_email: str) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...


@dataclass
class AsyncSMTPMailer(BaseAsyncMailer[SMTPConfig]):

    async def connect(self) -> Self:
        try:
            self.smtp_session = aiosmtplib.SMTP(
                hostname=self.config.smtp_server,
                port=self.config.smtp_port,
                username=self.config.smtp_user,
                password=self.config.smtp_password,
                use_tls=False,
                start_tls=False
            )
            await self.smtp_session.connect()
            await self.smtp_session.noop()
            self.config.logger.info('SMTP: connect')

        except Exception as e:
            self.config.logger.critical(e, exc_info=True)
            raise MailerError from e

        return self

    async def send(self, subject: str, body: str, to_email: str) -> None:
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.self_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            await self.smtp_session.send_message(msg)

        except aiosmtplib.SMTPRecipientsRefused as e:
            self.config.logger.debug('SMTP: Recipients refused')
            raise NonExistentEmail from e

        except Exception as e:
            self.config.logger.warning(e, exc_info=True)
            raise MailerError from e

    async def close(self) -> None:
        if self.smtp_session:
            self.smtp_session.close()
        self.config.logger.info('SMTP: close')
