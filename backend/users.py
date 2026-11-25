import psycopg
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from database import connect
from schemas import (
    PAGE_SIZE,
    US_STATES,
    SortColumn,
    SortOrder,
    User,
    UserCreate,
    UserUpdate,
)


router = APIRouter(
    prefix="/api/users",
    tags=["users"],
)

@router.post("", status_code=201)
def add_user(user: UserCreate):
    with connect() as conn:
        row = conn.execute(
            "INSERT INTO users (name, age, birth_state) VALUES (%s, %s, %s) RETURNING id",
            (user.name, user.age, user.birth_state,),
        ).fetchone()
    if row is None:
        raise RuntimeError("INSERT returned no user ID")
    return {"id": row[0], "name": user.name, "age":user.age, "birth_state": user.birth_state}


@router.get("", response_model=list[User])
def fetch_users(
    birth_state: str | None = None,
    page: int = Query(default=1, ge=1),
    sort_by: SortColumn = "id",
    order: SortOrder = "asc"
):
    # For pagination:
    limit = PAGE_SIZE # number of records per page
    offset = max(0, (page-1) * limit)  # offset number of records
    
    # Sorting:
    direction = psycopg.sql.SQL("DESC") if order == "desc" else psycopg.sql.SQL("ASC")
    where_clause = psycopg.sql.SQL("")
    params = []

    # Optional Filter, birth state:
    if birth_state is not None:
        birth_state = birth_state.strip().upper()
        if birth_state not in US_STATES:
            raise HTTPException(
                status_code=422,
                detail= {"code":"INVALID_STATE", "message":"Use a valid two-letter US state code"}
            )
        where_clause = psycopg.sql.SQL("WHERE birth_state = %s")
        params.append(birth_state)    

    query = psycopg.sql.SQL("""
        SELECT id, name, age, birth_state 
        FROM users 
        {where} 
        ORDER BY {sort_col} {direction}, id ASC 
        LIMIT %s OFFSET %s
    """).format(
        where=where_clause,
        sort_col=psycopg.sql.Identifier(sort_by),
        direction=direction,
    )
    params.extend([limit, offset])

    with connect() as conn:
        rows = conn.execute(query=query, params=params).fetchall()
    
    return [{"id": row[0], "name": row[1], "age": row[2], "birth_state": row[3]} for row in rows]


@router.get("/{id}", response_model=User)
def get_user(id: int):
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = (%s)", (id,)).fetchone()
        if row is not None:
            return {"id": row[0], "name": row[1], "age": row[2], "birth_state": row[3]}
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No User with ID: {id} in database"
            )


@router.put("/{id}", response_model=User)
def update_user(id: int, update: UserUpdate):
    row = get_user(id)
    row.update(update.model_dump(exclude_none=True))
    with connect() as conn:
        newRow = conn.execute(
            "UPDATE users SET name = (%s), age = (%s), birth_state = (%s) WHERE id = (%s) RETURNING id, name, age, birth_state",
            (row["name"], row["age"], row["birth_state"], id,)
        ).fetchone()
    return {"id": newRow[0], "name": newRow[1], "age": newRow[2], "birth_state": newRow[3]}


@router.delete("/{id}")
def delete_user(id: int):
    with connect() as conn:
        deleted_user = conn.execute("DELETE FROM users WHERE id = (%s) RETURNING *", (id,)).fetchone()
    
    if deleted_user is None:
        raise HTTPException(
                status_code=404,
                detail=f"No User with ID: {id} in database"
            )
            
    return JSONResponse(
        status_code=200,
        content={"Rows deleted": deleted_user}
    )