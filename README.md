**Ollama API App**
=====================================

**Table of Contents**
-------------------

- [**Ollama API App**](#ollama-api-app)
  - [**Table of Contents**](#table-of-contents)
  - [Introduction](#introduction)
    - [API Endpoints](#api-endpoints)
  - [GET /api/models](#get-apimodels)
    - [Endpoint: /api/models](#endpoint-apimodels)
  - [POST /api/generateo](#post-apigenerateo)
    - [Request Body:](#request-body)
  - [Method: POST](#method-post)
    - [Endpoint: /api/generate](#endpoint-apigenerate)
  - [Static Files](#static-files)

## Introduction
This is a Flask web application that interacts with the Ollama API. It allows users to fetch available models and generate responses based on prompts.

- [API Endpoints](#api-endpoints)

### API Endpoints

## GET /api/models
Fetches available models from the Ollama API.

### Endpoint: /api/models

## POST /api/generateo
Generates a response based on a prompt and model.

### Request Body:
* `prompt`: The text to generate a response for.
* `model`: The model to use (default: dolphin-mixtral).
* `temperature`: The temperature of the generated response (default: 0.7).

## Method: POST

### Endpoint: /api/generate

- [Static Files](#static-files)

## Static Files
Serves static files such as CSS and JavaScript.

- [Method: GET](#method-get)
- [Method: POST](#method-post)
