from oaas_sdk2_py import oaas, OaasObject
from oaas_sdk2_py.config import OaasConfig

oaas.configure(OaasConfig(mock_mode=True, async_mode=True))

@oaas.service("SessionCounter", package="examples")
class SessionCounter(OaasObject):
    count: int | None = None

    @oaas.method()
    async def increment_sessions(self) -> int:
        if not self.count:
            self.count = 0
        self.count += 1
        print(f"SessionCounter: Active sessions now {self.count}")
        return self.count

@oaas.service("UserManager", package="examples")
class UserManager(OaasObject):
    session_counter_id: int | None = None

    @oaas.constructor()
    def initialize(self, session_counter_id: int):
        print("UserManager: initialize")
        self.session_counter_id = session_counter_id

    @oaas.method()
    async def login_user(self, user_id: str) -> str:
        print(f"UserManager: User {user_id} attempting to log in.")
        if self.session_counter_id is not None:
            counter = SessionCounter.load(self.session_counter_id)
            await counter.increment_sessions()
        return f"User {user_id} logged in successfully."

async def main():
    
    # Create objects and interact
    print("-------")
    global_counter = SessionCounter.create(obj_id=100)
    global_counter.commit(force=True)
    print("-------")
    user_mgr = UserManager.create(obj_id=200)
    user_mgr.initialize(100)
    print("-------")
    print(await user_mgr.login_user("Alice"))
    print(await user_mgr.login_user("Bob"))
    print("Final session count:", SessionCounter.load(100).count)
    assert SessionCounter.load(100).count == 2

if __name__ == "__main__":
    
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    import asyncio
    asyncio.run(main())