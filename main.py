# Import FastMCP framework for creating MCP servers
from fastmcp import FastMCP
import os
import sqlite3

# Set database path relative to current file location
DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")

# Initialize FastMCP server with name "ExpenseTracker"
mcp = FastMCP("ExpenseTracker")

# Initialize database and create expenses table if it doesn't exist
def init_db():
    with sqlite3.connect(DB_PATH) as c:
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

# Create database on module load
init_db()

# Tool to add a new expense entry to the database
@mcp.tool()
def add_expense(date, amount, category, subcategory="", note=""):
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
            (date, amount, category, subcategory, note)
        )
        return {"status": "ok", "id": cur.lastrowid}

# Tool to retrieve all expenses within a date range
@mcp.tool()
def list_expenses(start_date, end_date):
    """
    List expense entries within an inclusive date range.
    """
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )
        # Convert query results to list of dictionaries
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

# Tool to get expense totals grouped by category
@mcp.tool()
def summarize(start_date, end_date, category=None):
    """
    Summarize expenses by category within an inclusive date range.
    Optionally filter by a specific category.
    """
    with sqlite3.connect(DB_PATH) as c:
        # Build query to sum amounts by category
        query = """
        SELECT category, SUM(amount) AS total_amount
        FROM expenses
        WHERE date BETWEEN ? AND ?
        """
        params = [start_date, end_date]
        
        # Add category filter if specified
        if category:
            query += " AND category = ?"
            params.append(category)
        
        query += " GROUP BY category ORDER BY category ASC"
        cur = c.execute(query, params)
        
        # Return results as list of dictionaries
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

# Start the server
# This conditional ensures the server only runs when the script is executed directly
# (not when imported as a module)
if __name__ == "__main__":
    # Run the MCP server with HTTP transport
    # host="0.0.0.0" makes it accessible from any network interface
    # port=8000 is the port number where the server will listen
    mcp.run(transport="http", host="0.0.0.0", port=8000)  #this means we are using our transport streamable http as remote server 

    #if we just write mcp.run() then it means that we are using our transport as stdio means deploying it as a local server