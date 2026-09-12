import os

from flask import Flask, jsonify

from modules.user.routes import user_bp

app = Flask(__name__)
app.register_blueprint(user_bp, url_prefix="/users")

PORT = int(os.environ.get("PORT", 5000))


@app.get("/")
def health():
    return jsonify(
        {
            "message": "User API is running",
            "endpoints": {
                "addUser": "POST /users",
                "fetchUsers": "GET /users",
                "fetchUserById": "GET /users/<id>",
                "updateUser": "PUT /users/<id>",
                "deleteUser": "DELETE /users/<id>",
            },
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
