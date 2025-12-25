from fastmcp import FastMCP
import os
import sqlite3
import tempfile
import json

# ---------------------------------------------------------
# Use system temporary directory (always writable)
# ---------------------------------------------------------
TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")

# Categories file stored next to this script
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

print(f"Database path: {DB_PATH}")

# ---------------------------------------------------------
# Create MCP Server
# ---------------------------------------------------------
mcp = FastMCP("ExpenseTracker")

# ---------------------------------------------------------
# Initialize SQLite database safely
# ---------------------------------------------------------
def init_db():
    try:
        with sqlite3.connect(DB_PATH) as c:
            # Enable WAL mode for better concurrency
            c.execute("PRAGMA journal_mode=WAL")

            # Create expenses table
            c.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT ''
                )
            """)

            # Test write access
            c.execute(
                "INSERT OR IGNORE INTO expenses(date, amount, category) VALUES ('2000-01-01', 0, 'test')"
            )
            c.execute("DELETE FROM expenses WHERE category = 'test'")
            c.commit()

        print("Database initialized successfully with write access")

    except Exception as e:
        print(f"Database initialization error: {e}")
        raise

# Initialize database at startup
init_db()

# ---------------------------------------------------------
# Tool: Add Expense
# ---------------------------------------------------------
@mcp.tool()
def add_expense(date, amount, category, subcategory="", note=""):
    """Add a new expense entry to the database."""
    try:
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute(
                """
                INSERT INTO expenses(date, amount, category, subcategory, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (date, amount, category, subcategory, note)
            )
            c.commit()

            return {
                "status": "success",
                "id": cur.lastrowid,
                "message": "Expense added successfully"
            }

    except sqlite3.OperationalError as e:
        if "readonly" in str(e).lower():
            return {
                "status": "error",
                "message": "Database is in read-only mode. Check file permissions."
            }
        return {"status": "error", "message": f"Database error: {str(e)}"}

    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}

# ---------------------------------------------------------
# Tool: List Expenses
# ---------------------------------------------------------
@mcp.tool()
def list_expenses(start_date, end_date):
    """List expenses within an inclusive date range."""
    try:
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute("""
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
            """, (start_date, end_date))

            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    except Exception as e:
        return {"status": "error", "message": f"Error listing expenses: {str(e)}"}

# ---------------------------------------------------------
# Tool: Summarize Expenses
# ---------------------------------------------------------
@mcp.tool()
def summarize(start_date, end_date, category=None):
    """Summarize expenses by category within a date range."""
    try:
        with sqlite3.connect(DB_PATH) as c:
            query = """
                SELECT category,
                       SUM(amount) AS total_amount,
                       COUNT(*) AS count
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """
            params = [start_date, end_date]

            if category:
                query += " AND category = ?"
                params.append(category)

            query += " GROUP BY category ORDER BY total_amount DESC"

            cur = c.execute(query, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    except Exception as e:
        return {"status": "error", "message": f"Error summarizing expenses: {str(e)}"}

# ---------------------------------------------------------
# Resource: Expense Categories (JSON)
# ---------------------------------------------------------
@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    """Return expense categories as JSON."""
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
        with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
            return f.read()

    except FileNotFoundError:
        return json.dumps(default_categories, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Could not load categories: {str(e)}"})


# Start the server
# This conditional ensures the server only runs when the script is executed directly
# (not when imported as a module)
if __name__ == "__main__":
    # Run the MCP server with HTTP transport
    # host="0.0.0.0" makes it accessible from any network interface
    # port=8000 is the port number where the server will listen
    mcp.run(transport="http", host="0.0.0.0", port=3001)  #this means we are using our transport streamable http as remote server 

    #if we just write mcp.run() then it means that we are using our transport as stdio means deploying it as a local server