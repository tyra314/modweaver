from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, cast

import aiohttp


class RemoteAPI(ABC):
    @property
    @abstractmethod
    def base_url(self) -> str:
        ...

    @property
    def _headers(self) -> Dict[str, str]:
        return {}

    async def __aenter__(self) -> "RemoteAPI":
        self._session: Optional[aiohttp.ClientSession] = aiohttp.ClientSession(
            raise_for_status=True, headers=self._headers
        )
        return self

    async def __aexit__(self, *err: Any) -> None:
        assert self._session is not None
        await self._session.close()
        self._session = None

    async def _get(self, path: str, **kwargs: Any) -> Dict["str", Any]:
        assert self._session is not None
        async with self._session.get(f"{self.base_url}{path}", **kwargs) as resp:
            return cast(Dict["str", Any], await resp.json())

    async def _post(self, path: str, **kwargs: Any) -> Dict["str", Any]:
        assert self._session is not None
        async with self._session.post(f"{self.base_url}{path}", **kwargs) as resp:
            return cast(Dict["str", Any], await resp.json())
