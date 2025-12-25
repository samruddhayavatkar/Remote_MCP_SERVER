# ---------------------------------------------------------
# Import required libraries
# ---------------------------------------------------------

from fastmcp import FastMCP          # FastMCP framework to create MCP server
import os                            # For file path handling
import aiosqlite                     # Async SQLite for non-blocking DB operations
import tempfile                      # To get system temporary directory


# ---------------------------------------------------------
# Database & File Paths
# ---------------------------------------------------------
# Use system temporary directory which is always writable.
# This avoids "database is read-only" permission errors.
# ---------------------------------------------------------

TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")

# Categories JSON file stored in the same directory as this script
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

print(f"Database path: {DB_PATH}")


# ---------------------------------------------------------
# Create the MCP Server
# ---------------------------------------------------------
# "ExpenseTracker" is the name shown to MCP clients
# ---------------------------------------------------------

mcp = FastMCP("ExpenseTracker")


# ---------------------------------------------------------
# Database Initialization (Synchronous)
# ---------------------------------------------------------
# This function:
# 1. Creates the database table if not present
# 2. Enables WAL mode for better concurrency
# 3. Tests write access to avoid runtime failures
# ---------------------------------------------------------

def init_db():
    try:
        # Use standard sqlite3 for one-time initialization
        import sqlite3

        with sqlite3.connect(DB_PATH) as c:
            # Enable Write-Ahead Logging (better concurrency)
            c.execute("PRAGMA journal_mode=WAL")

            # Create expenses table
            c.execute("""
                CREATE TABLE IF NOT EXISTS expenses(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT ''
                )
            """)

            # Insert and delete a test row to confirm write access
            c.execute(
                "INSERT OR IGNORE INTO expenses(date, amount, category) VALUES ('2000-01-01', 0, 'test')"
            )
            c.execute("DELETE FROM expenses WHERE category = 'test'")

            print("Database initialized successfully with write access")

    except Exception as e:
        # If initialization fails, stop execution immediately
        print(f"Database initialization error: {e}")
        raise


# ---------------------------------------------------------
# Initialize the database at startup
# ---------------------------------------------------------

init_db()


# ---------------------------------------------------------
# MCP Tool: Add Expense
# ---------------------------------------------------------
# Adds a new expense record to the database
# This function is async to avoid blocking the MCP server
# ---------------------------------------------------------

@mcp.tool()
async def add_expense(date, amount, category, subcategory="", note=""):
    """Add a new expense entry to the database."""
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            # Insert expense into database
            cur = await c.execute(
                """
                INSERT INTO expenses(date, amount, category, subcategory, note)
                VALUES (?,?,?,?,?)
                """,
                (date, amount, category, subcategory, note)
            )

            # Save changes
            await c.commit()

            return {
                "status": "success",
                "id": cur.lastrowid,
                "message": "Expense added successfully"
            }

    except Exception as e:
        # Handle read-only database error explicitly
        if "readonly" in str(e).lower():
            return {
                "status": "error",
                "message": "Database is in read-only mode. Check file permissions."
            }

        return {
            "status": "error",
            "message": f"Database error: {str(e)}"
        }


# ---------------------------------------------------------
# MCP Tool: List Expenses
# ---------------------------------------------------------
# Fetches all expenses within a given date range
# Results are ordered by newest first
# ---------------------------------------------------------

@mcp.tool()
async def list_expenses(start_date, end_date):
    """List expense entries within an inclusive date range."""
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute("""
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
            """, (start_date, end_date))

            # Convert rows into list of dictionaries
            cols = [d[0] for d in cur.description]
            rows = await cur.fetchall()

            return [dict(zip(cols, r)) for r in rows]

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error listing expenses: {str(e)}"
        }


# ---------------------------------------------------------
# MCP Tool: Summarize Expenses
# ---------------------------------------------------------
# Groups expenses by category and calculates:
# - Total amount
# - Number of transactions
# ---------------------------------------------------------

@mcp.tool()
async def summarize(start_date, end_date, category=None):
    """Summarize expenses by category within an inclusive date range."""
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            query = """
                SELECT category,
                       SUM(amount) AS total_amount,
                       COUNT(*) AS count
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """
            params = [start_date, end_date]

            # Optional category filter
            if category:
                query += " AND category = ?"
                params.append(category)

            query += " GROUP BY category ORDER BY total_amount DESC"

            cur = await c.execute(query, params)

            # Convert results to JSON-friendly format
            cols = [d[0] for d in cur.description]
            rows = await cur.fetchall()

            return [dict(zip(cols, r)) for r in rows]

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error summarizing expenses: {str(e)}"
        }


# ---------------------------------------------------------
# MCP Resource: Expense Categories
# ---------------------------------------------------------
# Exposes categories as a read-only JSON resource
# Accessible via: expense:///categories
# ---------------------------------------------------------

@mcp.resource("expense:///categories", mime_type="application/json")
def categories():
    """Return expense categories as a JSON resource."""
    
    # Default categories if file does not exist
    default_categories = {
        "categories": [
            "Food & Dining",
            "Transportation",
            "Shopping",
            "Entertainment",
            "Bills & Utilities",
            "Healthcare",
            "Travel",
            "Education",
            "Business",
            "Other"
        ]
    }

    try:
        # Try loading categories from file
        with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
            return f.read()

    except FileNotFoundError:
        # If file is missing, return default categories
        import json
        return json.dumps(default_categories, indent=2)

    except Exception as e:
        return f'{{"error": "Could not load categories: {str(e)}"}}'


# ---------------------------------------------------------
# Start the MCP Server
# ---------------------------------------------------------
# HTTP mode allows remote MCP clients to connect
# ---------------------------------------------------------

if __name__ == "__main__":
    mcp.run(
        transport="http",   # Run MCP over HTTP
        host="0.0.0.0",     # Accept connections from any IP
        port=8000           # Server port
    )

    # Alternative option:
    # mcp.run()
    # Runs over STDIO (recommended for Claude Desktop local usage)
