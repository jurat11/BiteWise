import logging
import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import img2pdf
from PIL import Image
import pytesseract
from docx import Document
from pdf2image import convert_from_path
from telegram import Bot

# Replace with your actual bot token
TOKEN = "8027102621:AAHcAP_XCFut_hYz0OVQZJ8jN6dTQaQkmj8"

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(TOKEN)


# Start command to show the menu
async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("Turn Images to File", callback_data='images_to_file')],
        [InlineKeyboardButton("Turn Image to LaTeX", callback_data='image_to_latex')],
        [InlineKeyboardButton("Generate LaTeX for Document", callback_data='document_to_latex')],
        [InlineKeyboardButton("Extract Text", callback_data='extract_text')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Please choose an option:', reply_markup=reply_markup)


# Handle button clicks
async def button(update: Update, context):
    query = update.callback_query
    await query.answer()
    state = context.user_data.get('state')

    if state == 'choosing_format':
        choice = query.data
        images = context.user_data.get('images', [])
        if choice in ['pdf', 'word', 'docx']:
            await query.message.reply_text('Processing your files, please wait...')
            try:
                if choice == 'pdf':
                    output_file = await convert_images_to_file(images, 'pdf')
                elif choice == 'word':
                    output_file = await convert_images_to_file(images, 'word')
                elif choice == 'docx':
                    output_file = await convert_images_to_file(images, 'docx')
                with open(output_file, 'rb') as f:
                    await query.message.reply_document(f)
                await query.message.reply_text('File processed successfully!')
            except Exception as e:
                logger.error(f"Error processing files: {str(e)}")
                await query.message.reply_text(f'Error: {str(e)}. Please try again.')
            finally:
                context.user_data['state'] = None
                context.user_data['images'] = []
                if 'temp_dir' in context.user_data:
                    for file in context.user_data['temp_dir']:
                        try:
                            os.remove(file)
                        except Exception as e:
                            logger.error(f"Error deleting file {file}: {str(e)}")
                    del context.user_data['temp_dir']
    else:
        choice = query.data
        if choice == 'images_to_file':
            await query.message.reply_text(
                'Upload images as files (use the paperclip icon, not the camera). Send /done when finished.')
            context.user_data['state'] = 'collecting_images'
            context.user_data['images'] = []
            context.user_data['temp_dir'] = []
        elif choice == 'image_to_latex':
            await query.message.reply_text('Upload a single image as a file (use the paperclip icon, not the camera).')
            context.user_data['state'] = 'waiting_for_image'
        elif choice == 'document_to_latex':
            await query.message.reply_text('Upload a PDF document.')
            context.user_data['state'] = 'waiting_for_document'
        elif choice == 'extract_text':
            await query.message.reply_text('Upload a photo or document as a file.')
            context.user_data['state'] = 'waiting_for_file'


# Handle file uploads and text messages
async def handle_message(update: Update, context):
    state = context.user_data.get('state')
    if not state:
        await update.message.reply_text('Please use /start to begin.')
        return

    if state == 'collecting_images':
        if update.message.text == '/done':
            images = context.user_data.get('images', [])
            if images:
                keyboard = [
                    [InlineKeyboardButton("PDF", callback_data='pdf')],
                    [InlineKeyboardButton("Word", callback_data='word')],
                    [InlineKeyboardButton("DOCX", callback_data='docx')],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text('Choose output format:', reply_markup=reply_markup)
                context.user_data['state'] = 'choosing_format'
            else:
                await update.message.reply_text('No images uploaded.')
        elif update.message.document:
            file_id = update.message.document.file_id
            if len(context.user_data['images']) < 1000:
                context.user_data['images'].append(file_id)
                await update.message.reply_text(
                    f'Image received ({len(context.user_data["images"])}/1000). Upload more or send /done.')
            else:
                await update.message.reply_text('Limit of 1000 images reached. Send /done to process.')
        else:
            await update.message.reply_text('Please upload images as files (not as photos) or send /done.')

    elif state == 'waiting_for_image':
        if update.message.document:
            file_id = update.message.document.file_id
            await update.message.reply_text('Processing image to LaTeX...')
            try:
                latex_code = await process_image_to_latex(file_id)
                await update.message.reply_text(latex_code)
            except Exception as e:
                logger.error(f"Error processing image to LaTeX: {str(e)}")
                await update.message.reply_text(f'Error: {str(e)}. Ensure the image is clear.')
            context.user_data['state'] = None
        else:
            await update.message.reply_text('Please upload an image as a file (not as a photo).')

    elif state == 'waiting_for_document':
        if update.message.document and update.message.document.mime_type == 'application/pdf':
            file_id = update.message.document.file_id
            await update.message.reply_text('Processing document to LaTeX...')
            try:
                latex_code = await process_document_to_latex(file_id)
                await update.message.reply_text(latex_code)
            except Exception as e:
                logger.error(f"Error processing document to LaTeX: {str(e)}")
                await update.message.reply_text(f'Error: {str(e)}')
            context.user_data['state'] = None
        else:
            await update.message.reply_text('Please upload a PDF document.')

    elif state == 'waiting_for_file':
        if update.message.document:
            file_id = update.message.document.file_id
            await update.message.reply_text('Extracting text...')
            try:
                text = await extract_text(file_id)
                await update.message.reply_text(text if text else 'No text extracted.')
            except Exception as e:
                logger.error(f"Error extracting text: {str(e)}")
                await update.message.reply_text(f'Error: {str(e)}')
            context.user_data['state'] = None
        else:
            await update.message.reply_text('Please upload a document as a file.')


# Convert images to specified file format
async def convert_images_to_file(file_ids, format_type):
    with tempfile.TemporaryDirectory() as tmpdirname:
        image_paths = []
        for i, file_id in enumerate(file_ids):
            file = await bot.get_file(file_id)
            image_path = os.path.join(tmpdirname, f'image_{i}.jpg')
            await file.download_to_drive(image_path)
            image_paths.append(image_path)
            context.user_data['temp_dir'].append(image_path)

        output_path = os.path.join(tmpdirname, f'output.{format_type}')
        if format_type == 'pdf':
            with open(output_path, 'wb') as f:
                f.write(img2pdf.convert(image_paths))
        elif format_type in ['word', 'docx']:
            doc = Document()
            for image_path in image_paths:
                doc.add_picture(image_path)
            doc.save(output_path)
        return output_path


# Process image to LaTeX (basic text extraction)
async def process_image_to_latex(file_id):
    with tempfile.TemporaryDirectory() as tmpdirname:
        file = await bot.get_file(file_id)
        image_path = os.path.join(tmpdirname, 'image.jpg')
        await file.download_to_drive(image_path)
        text = pytesseract.image_to_string(Image.open(image_path))
        latex_code = f'\\documentclass{{article}}\n\\begin{{document}}\n{text}\n\\end{{document}}'
        return latex_code


# Process PDF document to LaTeX (basic image extraction)
async def process_document_to_latex(file_id):
    with tempfile.TemporaryDirectory() as tmpdirname:
        file = await bot.get_file(file_id)
        pdf_path = os.path.join(tmpdirname, 'document.pdf')
        await file.download_to_drive(pdf_path)
        images = convert_from_path(pdf_path)
        latex_code = '\\documentclass{article}\n\\usepackage{graphicx}\n\\begin{document}\n'
        for i, img in enumerate(images):
            img_path = os.path.join(tmpdirname, f'img_{i}.jpg')
            img.save(img_path, 'JPEG')
            latex_code += f'\\includegraphics{{img_{i}.jpg}}\n'
        latex_code += '\\end{document}'
        return latex_code


# Extract text from file
async def extract_text(file_id):
    with tempfile.TemporaryDirectory() as tmpdirname:
        file = await bot.get_file(file_id)
        file_path = os.path.join(tmpdirname, 'file')
        await file.download_to_drive(file_path)
        text = pytesseract.image_to_string(Image.open(file_path))
        return text


# Main function to run the bot
def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, handle_message))
    application.run_polling()


if __name__ == '__main__':
    main()