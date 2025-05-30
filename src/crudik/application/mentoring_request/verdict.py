from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

from crudik.adapters.idp import TokenMentorIdProvider, UnauthorizedError
from crudik.application.common.uow import UoW
from crudik.application.errors.common import AccessDeniedError
from crudik.application.errors.mentoring_request import (
    MentoringRequestCannotBeUpdatedError,
    MentoringRequestNotFoundError,
)
from crudik.application.gateway.mentor_gateway import MentorGateway
from crudik.application.gateway.mentoring_request import MentoringRequestGateway
from crudik.models.mentoring_request import MentoringRequestType


class VerdictMentoringRequestType(Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class VerdictMentoringRequestQuery(BaseModel):
    mentoring_request_id: UUID = Field(description="Идентификатор запроса на менторинг")
    type: VerdictMentoringRequestType = Field(description="Тип вердикта")


@dataclass(frozen=True, slots=True)
class VerdictMentoringRequestByMentor:
    uow: UoW
    mentor_gateway: MentorGateway
    gateway: MentoringRequestGateway
    id_provider: TokenMentorIdProvider

    async def execute(self, request: VerdictMentoringRequestQuery) -> None:
        mentor_id = await self.id_provider.get_mentor_id()
        mentor = await self.mentor_gateway.get_by_id(mentor_id)
        if mentor is None:
            raise UnauthorizedError

        mentoring_request = await self.gateway.get_by_id(request.mentoring_request_id)
        if mentoring_request is None:
            raise MentoringRequestNotFoundError

        if mentoring_request.mentor_id != mentor_id:
            raise AccessDeniedError

        if mentoring_request.type != MentoringRequestType.REVIEW:
            raise MentoringRequestCannotBeUpdatedError

        mentoring_request.type = MentoringRequestType(request.type.value)
        await self.uow.commit()
