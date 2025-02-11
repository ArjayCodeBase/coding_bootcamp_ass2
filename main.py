import hashlib
from fastapi import FastAPI, HTTPException, Depends
import pymysql
from pydantic import BaseModel
from typing import List
from typing import Optional
from datetime import date
from datetime import datetime


app = FastAPI()


# Database connection
def get_db_connection():
    return pymysql.connect(
        host="127.0.0.1",
        user="root",
        password="",
        database="imss",
        cursorclass=pymysql.cursors.DictCursor
    )


# Models for Request/Response
class Category(BaseModel):
    id: int = None
    category_name: str

class Product(BaseModel):
    id: int = None
    product_name: str
    quantity: int
    description: str
    category: str
    price: int
    date_purchase: date
    expiration: date

class Supplier(BaseModel):
    id: int = None
    product_name: str
    supplier_name: str
    contact_name: str
    contact_number: int

class ProductReturn(BaseModel):
    id: int = None
    product_name: str
    quantity: int
    reason: str

class AdminRegister(BaseModel):
    username: str
    password: str

class AdminLogin(BaseModel):
    username: str
    password: str
    
class ProductLog(BaseModel):
    id: int
    product_id: int
    product_name: str
    quantity: int
    description: str
    category: str
    price: int
    action: str
    action_date: datetime
    admin_id: int

# Models
class AdminRegister(BaseModel):
    username: str
    password: str

class AdminLogin(BaseModel):
    username: str
    password: str

class AdminUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None

# Register Endpoint
@app.post("/register" , status_code=201)
def register(admin: AdminRegister):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("INSERT INTO admin (username, password) VALUES (%s, %s)", (admin.username, admin.password))
        conn.commit()
    conn.close()
    return {"message": "Admin registered successfully"}

# Login Endpoint
@app.post("/login")
def login(admin: AdminLogin):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM admin WHERE username = %s", (admin.username,))
        user = cursor.fetchone()
    conn.close()

    if not user or user['password'] != admin.password:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    return {"message": "Login successful", "user": admin.username}

# Update Admin Endpoint
@app.put("/admin/{admin_id}")
def update_admin(admin_id: int, admin: AdminUpdate):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM admin WHERE id = %s", (admin_id,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            raise HTTPException(status_code=404, detail="Admin not found")

        # Update only the fields that are provided
        update_fields = []
        update_values = []
        if admin.username:
            update_fields.append("username = %s")
            update_values.append(admin.username)
        if admin.password:
            update_fields.append("password = %s")
            update_values.append(admin.password)

        if update_fields:
            query = f"UPDATE admin SET {', '.join(update_fields)} WHERE id = %s"
            update_values.append(admin_id)
            cursor.execute(query, update_values)
            conn.commit()

    conn.close()
    return {"message": "Admin updated successfully"}

# Simple Logout Endpoint
@app.post("/logout")
def logout():
    return {"message": "Logout successful. Please clear any session data on the client-side."}

# Categories Endpoints
@app.get("/categories", response_model=List[Category])
def get_categories():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM categories")
        categories = cursor.fetchall()
    conn.close()
    return categories

@app.post("/categories", response_model=Category)
def create_category(category: Category):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("INSERT INTO categories (category_name) VALUES (%s)", (category.category_name,))
        conn.commit()
        category.id = cursor.lastrowid
    conn.close()
    return category

@app.put("/categories/{category_id}", response_model=Category)
def update_category(category_id: int, category: Category):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("UPDATE categories SET category_name = %s WHERE id = %s", (category.category_name, category_id))
        conn.commit()
    conn.close()
    return category

@app.delete("/categories/{category_id}")
def delete_category(category_id: int):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM categories WHERE id = %s", (category_id,))
        conn.commit()
    conn.close()
    return {"message": "Category deleted"}



@app.post("/products", response_model=Product)
def create_product(product: Product):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO products (product_name, quantity, description, category, price, date_purchase, expiration) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (product.product_name, product.quantity, product.description, product.category, 
              product.price, product.date_purchase, product.expiration))
        conn.commit()
        product.id = cursor.lastrowid
    conn.close()
    return product

@app.put("/products/{product_id}", response_model=Product)
def update_product(product_id: int, product: Product):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE products 
            SET product_name = %s, quantity = %s, description = %s, category = %s, price = %s, date_purchase = %s, expiration = %s
            WHERE id = %s
        """, (product.product_name, product.quantity, product.description, product.category, product.price, 
              product.date_purchase, product.expiration, product_id))
        conn.commit()
    conn.close()
    return product

# Products Endpoints
@app.get("/products", response_model=List[Product])
def get_products():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
    conn.close()
    return products

# View function to get product description by id
@app.get("/products/{product_id}/description")
def get_product_description(product_id: int):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT description FROM products WHERE id = %s", (product_id,))
        description = cursor.fetchone()
    conn.close()

    if not description:
        raise HTTPException(status_code=404, detail=f"No product found with id {product_id}")
    
    return description


# Function to log the deleted product
def log_deleted_product(product_name: str, quantity: int, price: int):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO history_log (product_name, quantity, price, date_history)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (product_name, quantity, price, datetime.now()))
            conn.commit()
    finally:
        conn.close()
        


# Route to delete a product
@app.delete("/delete_product/{product_id}")
async def delete_product(product_id: int):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Fetch the product information before deletion
            select_sql = "SELECT product_name, quantity, price FROM products WHERE id = %s"
            cursor.execute(select_sql, (product_id,))
            product = cursor.fetchone()

            if product is None:
                raise HTTPException(status_code=404, detail="Product not found")

            # Insert the deleted product into history_log
            log_deleted_product(product['product_name'], product['quantity'], product['price'])

            # Delete the product from the products table
            delete_sql = "DELETE FROM products WHERE id = %s"
            cursor.execute(delete_sql, (product_id,))
            conn.commit()

            return {"message": "Product deleted and logged in history"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        conn.close()
        

@app.post("/suppliers", response_model=Supplier)
def create_supplier(supplier: Supplier):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO suppliers (product_name, supplier_name, contact_name, contact_number) 
                VALUES (%s, %s, %s, %s)
            """, (supplier.product_name, supplier.supplier_name, supplier.contact_name, supplier.contact_number))
            conn.commit()
            supplier.id = cursor.lastrowid  # Assigning last inserted ID to the supplier object
    finally:
        conn.close()  # Ensure the connection is closed
    return supplier



@app.put("/suppliers/{supplier_id}", response_model=Supplier)
def update_supplier(supplier_id: int, supplier: Supplier):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE suppliers 
            SET supplier_name = %s, contact_name = %s, contact_number = %s
            WHERE id = %s
        """, (supplier.supplier_name, supplier.contact_name, supplier.contact_number, supplier_id))
        conn.commit()
    conn.close()
    return supplier

# Suppliers Endpoints
@app.get("/suppliers", response_model=List[Supplier])
def get_suppliers():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM suppliers")
        suppliers = cursor.fetchall()
    conn.close()
    return suppliers

@app.delete("/suppliers/{supplier_id}")
def delete_supplier(supplier_id: int):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM suppliers WHERE id = %s", (supplier_id,))
        conn.commit()
    conn.close()
    return {"message": "Supplier deleted"}


@app.post("/product_returns", response_model=ProductReturn)
def create_product_return(product_return: ProductReturn):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO product_return (product_name, quantity, reason) 
            VALUES (%s, %s, %s)
        """, (product_return.product_name, product_return.quantity, product_return.reason))
        conn.commit()
        product_return.id = cursor.lastrowid
    conn.close()
    return product_return


@app.put("/product_returns/{return_id}", response_model=ProductReturn)
def update_product_return(return_id: int, product_return: ProductReturn):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE product_return 
            SET product_name = %s, quantity = %s, reason = %s
            WHERE id = %s
        """, (product_return.product_name, product_return.quantity, product_return.reason, return_id))
        conn.commit()
    conn.close()
    return product_return

# Product Return Endpoints
@app.get("/product_returns", response_model=List[ProductReturn])
def get_product_returns():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM product_return")
        returns = cursor.fetchall()
    conn.close()
    return returns

# View function to get the reason for a specific product return
@app.get("/product_return/{return_id}/reason")
def get_product_return_reason(return_id: int):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT reason FROM product_return WHERE id = %s", (return_id,))
        reason = cursor.fetchone()
    conn.close()

    if not reason:
        raise HTTPException(status_code=404, detail=f"No return found with id {return_id}")
    
    return reason

@app.delete("/product_returns/{return_id}")
def delete_product_return(return_id: int):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM product_return WHERE id = %s", (return_id,))
        conn.commit()
    conn.close()
    return {"message": "Product return deleted"}

# Route to view product history log
@app.get("/history_log", response_model=List[dict])
async def get_history_log():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT id, product_name, quantity, price, date_history FROM history_log ORDER BY date_history DESC"
            cursor.execute(sql)
            logs = cursor.fetchall()

            if not logs:
                raise HTTPException(status_code=404, detail="No history log entries found")

            return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        conn.close()
        
        
@app.delete("/history_log/{date}")
def delete_history_log(date: str):
    try:
        # Parse the date string to a datetime object
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Delete logs from the specified date
            delete_sql = "DELETE FROM history_log WHERE DATE(date_history) = %s"
            cursor.execute(delete_sql, (date_obj.strftime('%Y-%m-%d'),))
            affected_rows = cursor.rowcount
            conn.commit()

            if affected_rows == 0:
                raise HTTPException(status_code=404, detail="No logs found for the specified date")

            return {"message": f"Deleted {affected_rows} log(s) for {date_obj.strftime('%Y-%m-%d')}"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        conn.close()
        
        
        
        
        
        
        
# View function to get the total quantity from the products table
@app.get("/products/total_quantity")
def get_total_product_quantity():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT SUM(quantity) AS total_quantity FROM products")
        result = cursor.fetchone()
    conn.close()

    if result is None or result['total_quantity'] is None:
        raise HTTPException(status_code=404, detail="No product quantity data found")
    
    return {"total_quantity": result['total_quantity']}


# View function to get the count of products with quantity below 10
@app.get("/products/low_stock_quantity")
def get_low_stock_quantity():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Count the number of products with quantity below 10
            cursor.execute("SELECT COUNT(*) AS low_stock_count FROM products WHERE quantity < 10")
            result = cursor.fetchone()
    finally:
        conn.close()

    # Return count; default to 0 if no low stock data
    low_stock_count = result['low_stock_count'] if result and result['low_stock_count'] is not None else 0
    
    return {"low_stock_quantity": low_stock_count}


# View function to get the total count of entries in the product_return table
@app.get("/product_return/total_count")
def get_total_product_return_count():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total_count FROM product_return")
        result = cursor.fetchone()
    conn.close()

    if result is None or result['total_count'] is None:
        raise HTTPException(status_code=404, detail="No product return data found")
    
    return {"total_count": result['total_count']}


# View function to get the total count of unique categories
@app.get("/categories/total_count")
def get_total_categories_count():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Correct column name `category` used here
            cursor.execute("SELECT COUNT(DISTINCT category) AS total_count FROM products")
            result = cursor.fetchone()
    finally:
        conn.close()

    # Return 0 if no categories are found
    total_count = result['total_count'] if result and result['total_count'] is not None else 0
    
    return {"total_count": total_count}