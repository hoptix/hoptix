import assemblyai as aai
from pinecone import Pinecone, ServerlessSpec
import assemblyai as aai
import requests
import os
from pydub import AudioSegment
import mimetypes
import wave
from nemo.collections.asr.models import EncDecSpeakerLabelModel
import torch
import numpy as np
import uuid
from sklearn.metrics.pairwise import cosine_similarity

