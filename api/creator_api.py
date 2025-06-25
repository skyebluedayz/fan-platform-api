import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy.orm import sessionmaker
from models.creator_models import engine, Creator, Category, Tag, UserFavorite, User
import json
from datetime import datetime

# 以下は既存のコードと同じ...
