from flask import Flask
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (JWTManager)
from flask_cors import CORS


app = Flask(__name__)

# init cors
CORS(app)

# adding JWT to the app
jwt = JWTManager(app)

# basedir  = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://root:Japanitoes@localhost:3306/fuprox"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

#app bindings
bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
ma = Marshmallow(app)