import pytest
from app.api.deps import get_current_user
from app.models.user import User

async def mock_get_current_user():
    user = User()
    user.id = 1
    user.email = "test@example.com"
    return user

@pytest.fixture(autouse=True)
def override_get_current_user():
    from app.main import app
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
