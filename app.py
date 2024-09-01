
from dotenv import load_dotenv
import base64
import streamlit as st
import os
import io
from PIL import Image 
import fitz  # PyMuPDF
import google.generativeai as genai
import re
import concurrent.futures

# Load environment variables
load_dotenv()

# Configure the generative AI model with API key
#genai.configure(api_key=os.getenv('GENAI_API_KEY'))
genai.configure(api_key='AIzaSyCbUpPCrYvJUJAKYkF3JJ5AsjxNUUBMe2M')

# Function to get response from Gemini AI model
def get_gemini_response(input, pdf_content, prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([input, pdf_content[0], prompt])
    return response.text

# Function to convert PDF pages to images using PyMuPDF
def convert_pdf_to_images(uploaded_file):
    pdf_document = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    images = []
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap()
        images.append(pix.tobytes())  # Convert to bytes format for further processing
    return images

# Function to handle multiple resume uploads (using convert_pdf_to_images)
def input_pdf_setup(uploaded_files):
    pdf_contents = []
    for uploaded_file in uploaded_files:
        # Convert first page to image using PyMuPDF
        images = convert_pdf_to_images(uploaded_file)
        first_image = images[0]  # Use the first image

        # Convert to bytes
        img_byte_arr = io.BytesIO()
        img = Image.open(io.BytesIO(first_image))  # Convert bytes back to image
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()

        pdf_part = {
            "mime_type": "image/jpeg",
            "data": base64.b64encode(img_byte_arr).decode()  # Encode to base64
        }
        pdf_contents.append(pdf_part)
    return pdf_contents

# Function to extract percentage from AI response
def extract_percentage(response_text):
    match = re.search(r'(\d+)%', response_text)
    if match:
        return int(match.group(1))
    return 0  # Return 0 if no percentage is found

# Function to process each resume
def process_resume(uploaded_file, input_prompt, input_text):
    pdf_content = input_pdf_setup([uploaded_file])
    response = get_gemini_response(input_prompt, pdf_content, input_text)
    percentage = extract_percentage(response)
    return (uploaded_file.name, percentage, response)

# Streamlit App
st.set_page_config(page_title="ATS Resume Expert")
st.header("ATS Tracking System")

# Input job description
input_text = st.text_area("Job Description: ", key="input")

# Multiple file uploader for resumes
uploaded_files = st.file_uploader("Upload your resumes (PDFs)...", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    st.write(f"{len(uploaded_files)} PDF(s) Uploaded Successfully")

# Define button actions
submit1 = st.button("Evaluate Resumes")
submit3 = st.button("Find Top Matching Resumes")

# Prompts
input_prompt1 = """
You are an experienced Technical Human Resource Manager, and your task is to review the provided resume against the job description.
Provide a short evaluation. Limit the strengths, weaknesses, and areas of improvement to a few words. Highlight missing keywords briefly.
"""

input_prompt3 = """
You are an ATS scanner. Evaluate the resume against the job description, return a match percentage, and provide a concise evaluation.
List missing keywords briefly. Keep strengths, weaknesses, and areas for improvement short and to the point.
"""

# If "Evaluate Resumes" is clicked
if submit1:
    if uploaded_files:
        # Parallel processing resumes for evaluation
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(process_resume, uploaded_file, input_prompt1, input_text)
                for uploaded_file in uploaded_files
            ]
            for future in concurrent.futures.as_completed(futures):
                resume_name, _, response = future.result()

                st.subheader(f"Evaluation for {resume_name}:")
                st.write(response)
    else:
        st.write("Please upload at least one resume.")

# If "Find Top Matching Resumes" is clicked
elif submit3:
    if uploaded_files:
        results = []
        # Parallel processing resumes to find the top match
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(process_resume, uploaded_file, input_prompt3, input_text)
                for uploaded_file in uploaded_files
            ]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        # Sort results by percentage match (descending order)
        sorted_results = sorted(results, key=lambda x: x[1], reverse=True)

        st.subheader("Top Matching Resumes (High to Low):")
        for resume_name, percentage, response in sorted_results:
            st.write(f"Resume: {resume_name}")
            st.write(f"Percentage Match: {percentage}%")
            st.write(f"Response: {response}")
            st.write("---")
    else:
        st.write("Please upload at least one resume.")
