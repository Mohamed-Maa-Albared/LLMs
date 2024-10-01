**Functional Requirements Document**
=====================================

**Table of Contents**
-------------------

- [**Functional Requirements Document**](#functional-requirements-document)
  - [**Table of Contents**](#table-of-contents)
  - [Features to be Added](#features-to-be-added)
    - [Voice Mode](#voice-mode)
      - [Description](#description)
      - [User Flow](#user-flow)
      - [Technical Requirements](#technical-requirements)
    - [Retrieval Augmented Generation](#retrieval-augmented-generation)
      - [Description](#description-1)
    - [PersistentModel](#persistentmodel)
      - [Description](#description-2)
- [Initialize once](#initialize-once)
- [Use in your main function](#use-in-your-main-function)
    - [Controller model](#controller-model)
      - [Description](#description-3)
      - [User Flow](#user-flow-1)
      - [Technical Requirements](#technical-requirements-1)
    - [step by step model (mO model)](#step-by-step-model-mo-model)
      - [Description](#description-4)
      - [User Flow](#user-flow-2)

## Features to be Added
------------------------

### Voice Mode
---------------

#### Description
Implement a feature that enables users to interact with the model using voice commands ,check if you can use whisper for that.

#### User Flow
1. Click on the icon with headphones in the text input.
2. A new interface is displayed, allowing users to speak into their device's microphone.
3. The spoken words are transcribed into text and sent to the model for processing.
4. The model's response is converted back into voice and played through the user's device.

#### Technical Requirements
* Integrate speech-to-text functionality using a reliable library or API.
* Develop a new interface for voice mode, ensuring seamless integration with the existing UI.
* Implement text-to-speech functionality to convey the model's responses in voice format.

### Retrieval Augmented Generation
-------------------------------

#### Description
To be determined (TBD). This feature will be planned and prioritized based on future requirements and feasibility assessments.
Idea 1: use a web search API like DuckDuckGO to retrieve relevant results.


### PersistentModel
-------------------------------

#### Description
for faster Inference, test first prompt compared with the ones after it.  
class PersistentModel:
    def __init__(self, model_name):
        self.model = ollama.create(model_name)

    def generate(self, prompt, temperature, max_tokens):
        return self.model.generate(prompt, temperature=temperature, max_tokens=max_tokens)

# Initialize once
persistent_model = PersistentModel("your_model_name")

# Use in your main function
def generate_response(prompt, temperature, max_tokens):
    return persistent_model.generate(prompt, temperature, max_tokens)


### Controller model 
---------------

#### Description
Use a fast model 1b or 3b to chose the best tool (model) for the job.


#### User Flow
1. It should be the same without any interruptions to the UX.

#### Technical Requirements
* Call the O models for example if the task is hard and the user can wait.
* Call the code model for coding tasks.
* call "small" models for conversations.
* Recreate the prompts in some cases where it makes sense (TBD)
* Call RAG for Data related tasks.
* Call audio model for voice files.


### step by step model (mO model)
---------------

#### Description
Use a fast model 1b or 3b to chose the best tool (model) for the job.

#### User Flow
1. It should be the same without any interruptions to the UX.