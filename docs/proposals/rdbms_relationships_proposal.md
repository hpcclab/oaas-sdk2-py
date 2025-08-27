# Proposal: Simple RDBMS-style Relationships for OaaS Objects (Interface Only)

Scope: Interface-only design. Provide clear, minimal primitives to model common RDBMS-like relationships between OaaS objects: Foreign Key (N:1), One-to-One (1:1), One-to-Many (1:N), and Many-to-Many (N:M). Relationships use identity-based references under the hood (ObjectMetadata) and expose a friendly API for navigation and updates.

## Goals
- Familiar relationship modeling similar to ORM/RDBMS.
- Keep declaration and usage simple and type-safe.
- No backend details; compatible with existing object-reference semantics.

## Relationship Field Types (Descriptors)
All descriptors are declared as annotated class attributes. They are async-aware but interface does not require awaiting for simple attribute access.

1) Foreign Key (N:1)
- `oaas.ForeignKey[T](nullable: bool = True, backref: str | None = None, on_delete: Literal["restrict", "nullify", "cascade"] = "restrict")`
- Access returns a proxy `T | None` (by identity); assignable via instance, proxy, or ObjectMetadata.

2) One-to-One (1:1)
- `oaas.OneToOne[T](nullable: bool = True, backref: str | None = None, on_delete: Literal["restrict", "nullify", "cascade"] = "restrict", unique: bool = True)`
- Access returns a proxy `T | None`; assignment enforces uniqueness across owners.

3) One-to-Many (1:N)
- `oaas.OneToMany[T](backref: str | None = None, order_by: str | None = None)`
- Access returns a relation view `RelationSet[T]` with:
  - `async add(item: T | ObjectRef[T] | ObjectMetadata) -> None`
  - `async remove(item: T | ObjectRef[T] | ObjectMetadata) -> None`
  - `async all() -> list[T]` (proxies)
  - `async count() -> int`
  - sync helpers: `__iter__()` yields proxies lazily (optional), `__len__()` may be O(1|N) depending on impl

4) Many-to-Many (N:M)
- `oaas.ManyToMany[T](backref: str | None = None)`
- Access returns a relation view `RelationSet[T]` with the same methods as above.

Notes
- `backref` (if provided) declares the inverse attribute name on the related class; when set, both sides stay consistent.
- All relations serialize as identities (ObjectMetadata) and never embed full state.

## Validation (Interface Level)
- Declared type `T` must be an OaaS service class.
- Assignments must be normalizable to references; otherwise `TypeError`.
- `backref` must refer to a compatible relation type on `T` (checked at class creation time); otherwise `ValueError`.
- For One-to-One, uniqueness is enforced (interface guarantee); violations raise `ValueError`.

## Simple Examples

### 1) N:1 (Foreign Key) User → Profile
```python
@oaas.service("Profile", package="example")
class Profile(OaasObject):
    email: str = ""

@oaas.service("User", package="example")
class User(OaasObject):
    # user.profile_id is implied by the FK; stored as identity
    profile: oaas.ForeignKey[Profile](nullable=True, backref="users")

    @oaas.method()
    async def link_profile(self, p: Profile | ObjectMetadata) -> bool:
        self.profile = p
        return True
```

`user.profile` returns a proxy to `Profile` (or None). `profile.users` is a OneToMany inferred by backref.

### 2) 1:1 Organization ↔ Logo
```python
@oaas.service("Logo", package="example")
class Logo(OaasObject):
    uri: str = ""

@oaas.service("Org", package="example")
class Org(OaasObject):
    logo: oaas.OneToOne[Logo](nullable=True, backref="org")
```

`org.logo` and `logo.org` reflect each other. Only one org can hold a given logo at a time.

### 3) 1:N Blog ↔ Post
```python
@oaas.service("Post", package="example")
class Post(OaasObject):
    title: str = ""
    # backref set by Blog.posts

@oaas.service("Blog", package="example")
class Blog(OaasObject):
    posts: oaas.OneToMany[Post](backref="blog")

    @oaas.method()
    async def add_post(self, p: Post):
        await self.posts.add(p)
```

### 4) N:M Student ↔ Course
```python
@oaas.service("Student", package="example")
class Student(OaasObject):
    courses: oaas.ManyToMany[Course](backref="students")

@oaas.service("Course", package="example")
class Course(OaasObject):
    students: oaas.ManyToMany[Student](backref="courses")
```

## Behavior Guarantees (Interface)
- Attribute access returns proxies (or relation views) without needing extra calls.
- Mutations via assignment (`ForeignKey`, `OneToOne`) or `RelationSet.add/remove` keep both sides consistent when `backref` is defined.
- Deletions on the owning side honor `on_delete` policy (restrict/nullify/cascade) at the interface level.

## Interop with Accessors
- `@oaas.getter/@oaas.setter` work with relation fields; getters return proxies or views, setters accept assignable forms (instance/ref/metadata), and can wrap `RelationSet.add/remove` for collections.

## Quick Reference
- FK: `profile: oaas.ForeignKey[Profile](nullable=True, backref="users")`
- 1:1: `logo: oaas.OneToOne[Logo](nullable=True, backref="org")`
- 1:N: `posts: oaas.OneToMany[Post](backref="blog")`
- N:M: `courses: oaas.ManyToMany[Course](backref="students")`

## Non-Goals (for this proposal)
- Query language, joins, or advanced filtering (can be layered later).
- Transaction semantics across multiple objects.
- Storage/indexing layout or RPC protocol specifics.
