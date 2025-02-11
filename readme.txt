uvicorn main:app --reload

python -m venv myenv
myenv\Scripts\activate

pip install fastapi pydantic pymysql uvicorn