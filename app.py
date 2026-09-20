import os
import pymysql
import boto3
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Retrieve configuration securely from environment variables
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME", "studentdb")

# Boto3 client automatically uses the EC2 IAM Instance Profile
s3_client = boto3.client('s3')

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name")
    email = request.form.get("email")
    course = request.form.get("course")
    file = request.files.get("photo")

    if not file or file.filename == '':
        return render_template("index.html", message="Error: Photo is required.")

    filename = secure_filename(file.filename)

    try:
        # 1. Upload photo to S3
        s3_client.upload_fileobj(
            file,
            BUCKET_NAME,
            filename,
            ExtraArgs={"ContentType": file.content_type}
        )
        photo_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{filename}"

        # 2. Insert student record into RDS MySQL
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                sql = "INSERT INTO students (name, email, course, photo_url) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql, (name, email, course, photo_url))
            connection.commit()
        finally:
            connection.close()

        return render_template("index.html", message=f"Student {name} registered successfully!")

    except Exception as e:
        return render_template("index.html", message=f"Error: {str(e)}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
