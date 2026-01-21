<<<<<<< HEAD
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)

def format_datetime(dt):
    """Format datetime to dd-mm-yyyy h:m AM/PM format"""
    if isinstance(dt, datetime):
        # Format: dd-mm-yyyy h:m AM/PM
        return dt.strftime('%d-%m-%Y %I:%M %p')
    elif dt and dt != 'N/A':
        # Try to parse if it's a string datetime
        try:
            if isinstance(dt, str):
                # Try common datetime formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S.%f']:
                    try:
                        parsed_dt = datetime.strptime(dt, fmt)
                        return parsed_dt.strftime('%d-%m-%Y %I:%M %p')
                    except ValueError:
                        continue
        except:
            pass
        return str(dt)
    return 'N/A'

def send_email_report(report_data):
    try:
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')
        # Support both EMAIL_TO and RECIPIENT_EMAIL for compatibility
        recipient_email = os.getenv('EMAIL_TO') or os.getenv('RECIPIENT_EMAIL')
        smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')  # Default to Gmail
        smtp_port = int(os.getenv('SMTP_PORT', '587'))  # Default to 587
        
        if not all([smtp_user, smtp_password, recipient_email]):
            missing_vars = []
            if not smtp_user:
                missing_vars.append('SMTP_USER')
            if not smtp_password:
                missing_vars.append('SMTP_PASSWORD')
            if not recipient_email:
                missing_vars.append('EMAIL_TO or RECIPIENT_EMAIL')
            raise Exception(f"Missing required email environment variables: {', '.join(missing_vars)}. Please check your .env file.")
        
        # Parse recipient emails (support comma-separated emails)
        recipient_emails = [email.strip() for email in recipient_email.split(',') if email.strip()]
        if not recipient_emails:
            raise Exception("No valid recipient emails found. Please check EMAIL_TO or RECIPIENT_EMAIL in your .env file.")
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Scraping Report - {report_data.get('id', 'N/A')}"
        msg['From'] = smtp_user
        msg['To'] = ', '.join(recipient_emails)  # Multiple recipients separated by comma
        
        # Format report data
        start_time = format_datetime(report_data.get('start_date_time', 'N/A'))
        end_time = format_datetime(report_data.get('end_date_time', 'N/A'))
        created_at = format_datetime(report_data.get('created_at', 'N/A'))
        
        duration = 'N/A'
        if report_data.get('start_date_time') and report_data.get('end_date_time'):
            try:
                if isinstance(report_data.get('start_date_time'), datetime) and isinstance(report_data.get('end_date_time'), datetime):
                    duration_timedelta = report_data.get('end_date_time') - report_data.get('start_date_time')
                    duration_seconds = duration_timedelta.total_seconds()
                    hours = int(duration_seconds // 3600)
                    minutes = int((duration_seconds % 3600) // 60)
                    seconds = int(duration_seconds % 60)
                    duration = f"{hours}h {minutes}m {seconds}s"
            except:
                pass
        
        # HTML email body
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                h2 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:hover {{ background-color: #f5f5f5; }}
                .success {{ color: #4CAF50; font-weight: bold; }}
                .failed {{ color: #f44336; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Scraping Report Summary</h2>
                <table>
                    <tr>
                        <th>Field</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td><strong>Report ID</strong></td>
                        <td>{report_data.get('id', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td><strong>Start Date & Time</strong></td>
                        <td>{start_time}</td>
                    </tr>
                    <tr>
                        <td><strong>End Date & Time</strong></td>
                        <td>{end_time}</td>
                    </tr>
                    <tr>
                        <td><strong>Duration</strong></td>
                        <td>{duration}</td>
                    </tr>
                    <tr>
                        <td><strong>Total Pages</strong></td>
                        <td>{report_data.get('total_pages', 0)}</td>
                    </tr>
                    <tr>
                        <td><strong>Total Items</strong></td>
                        <td>{report_data.get('total_items', 0)}</td>
                    </tr>
                    <tr>
                        <td><strong>Success Listing Pages</strong></td>
                        <td class="success">{report_data.get('success_listing_pages', 0)}</td>
                    </tr>
                    <tr>
                        <td><strong>Failed Listing Pages</strong></td>
                        <td class="failed">{report_data.get('failed_listing_pages', 0)}</td>
                    </tr>
                    <tr>
                        <td><strong>Success Details Pages</strong></td>
                        <td class="success">{report_data.get('success_details_pages', 0)}</td>
                    </tr>
                    <tr>
                        <td><strong>Failed Details Pages</strong></td>
                        <td class="failed">{report_data.get('failed_details_pages', 0)}</td>
                    </tr>
                    <tr>
                        <td><strong>Created At</strong></td>
                        <td>{created_at}</td>
                    </tr>
                </table>
                <p><em>This is an automated report generated by the scraping system.</em></p>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_body = f"""
Scraping Report Summary
========================

Report ID: {report_data.get('id', 'N/A')}
Start Date & Time: {start_time}
End Date & Time: {end_time}
Duration: {duration}
Total Pages: {report_data.get('total_pages', 0)}
Total Items: {report_data.get('total_items', 0)}
Success Listing Pages: {report_data.get('success_listing_pages', 0)}
Failed Listing Pages: {report_data.get('failed_listing_pages', 0)}
Success Details Pages: {report_data.get('success_details_pages', 0)}
Failed Details Pages: {report_data.get('failed_details_pages', 0)}
Created At: {created_at}

This is an automated report generated by the scraping system.
        """
        
        # Attach both versions
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email via SMTP server
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg, to_addrs=recipient_emails)
        
        logger.info(f"Email report sent successfully to {', '.join(recipient_emails)}")
        return True
        
    except Exception as e:
        error_msg = f"Error sending email report: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)
=======
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)

def format_datetime(dt):
    """Format datetime to dd-mm-yyyy h:m AM/PM format"""
    if isinstance(dt, datetime):
        # Format: dd-mm-yyyy h:m AM/PM
        return dt.strftime('%d-%m-%Y %I:%M %p')
    elif dt and dt != 'N/A':
        # Try to parse if it's a string datetime
        try:
            if isinstance(dt, str):
                # Try common datetime formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S.%f']:
                    try:
                        parsed_dt = datetime.strptime(dt, fmt)
                        return parsed_dt.strftime('%d-%m-%Y %I:%M %p')
                    except ValueError:
                        continue
        except:
            pass
        return str(dt)
    return 'N/A'

def send_email_report(report_data):
    try:
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')
        # Support both EMAIL_TO and RECIPIENT_EMAIL for compatibility
        recipient_email = os.getenv('EMAIL_TO') or os.getenv('RECIPIENT_EMAIL')
        smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')  # Default to Gmail
        smtp_port = int(os.getenv('SMTP_PORT', '587'))  # Default to 587
        
        if not all([smtp_user, smtp_password, recipient_email]):
            missing_vars = []
            if not smtp_user:
                missing_vars.append('SMTP_USER')
            if not smtp_password:
                missing_vars.append('SMTP_PASSWORD')
            if not recipient_email:
                missing_vars.append('EMAIL_TO or RECIPIENT_EMAIL')
            raise Exception(f"Missing required email environment variables: {', '.join(missing_vars)}. Please check your .env file.")
        
        # Parse recipient emails (support comma-separated emails)
        recipient_emails = [email.strip() for email in recipient_email.split(',') if email.strip()]
        if not recipient_emails:
            raise Exception("No valid recipient emails found. Please check EMAIL_TO or RECIPIENT_EMAIL in your .env file.")
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Scraping Report - {report_data.get('id', 'N/A')}"
        msg['From'] = smtp_user
        msg['To'] = ', '.join(recipient_emails)  # Multiple recipients separated by comma
        
        # Format report data
        start_time = format_datetime(report_data.get('start_date_time', 'N/A'))
        end_time = format_datetime(report_data.get('end_date_time', 'N/A'))
        created_at = format_datetime(report_data.get('created_at', 'N/A'))
        
        duration = 'N/A'
        if report_data.get('start_date_time') and report_data.get('end_date_time'):
            try:
                if isinstance(report_data.get('start_date_time'), datetime) and isinstance(report_data.get('end_date_time'), datetime):
                    duration_timedelta = report_data.get('end_date_time') - report_data.get('start_date_time')
                    duration_seconds = duration_timedelta.total_seconds()
                    hours = int(duration_seconds // 3600)
                    minutes = int((duration_seconds % 3600) // 60)
                    seconds = int(duration_seconds % 60)
                    duration = f"{hours}h {minutes}m {seconds}s"
            except:
                pass
        
        # HTML email body
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                h2 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:hover {{ background-color: #f5f5f5; }}
                .success {{ color: #4CAF50; font-weight: bold; }}
                .failed {{ color: #f44336; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Scraping Report Summary</h2>
                <table>
                    <tr>
                        <th>Field</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td><strong>Report ID</strong></td>
                        <td>{report_data.get('id', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td><strong>Start Date & Time</strong></td>
                        <td>{start_time}</td>
                    </tr>
                    <tr>
                        <td><strong>End Date & Time</strong></td>
                        <td>{end_time}</td>
                    </tr>
                    <tr>
                        <td><strong>Duration</strong></td>
                        <td>{duration}</td>
                    </tr>
                    <tr>
                        <td><strong>Total Pages</strong></td>
                        <td>{report_data.get('total_pages', 0)}</td>
                    </tr>
                    <tr>
                        <td><strong>Total Items</strong></td>
                        <td>{report_data.get('total_items', 0)}</td>
                    </tr>
                    <tr>
                        <td><strong>Success Listing Pages</strong></td>
                        <td class="success">{report_data.get('success_listing_pages', 0)}</td>
                    </tr>
                    <tr>
                        <td><strong>Failed Listing Pages</strong></td>
                        <td class="failed">{report_data.get('failed_listing_pages', 0)}</td>
                    </tr>
                    <tr>
                        <td><strong>Success Details Pages</strong></td>
                        <td class="success">{report_data.get('success_details_pages', 0)}</td>
                    </tr>
                    <tr>
                        <td><strong>Failed Details Pages</strong></td>
                        <td class="failed">{report_data.get('failed_details_pages', 0)}</td>
                    </tr>
                    <tr>
                        <td><strong>Created At</strong></td>
                        <td>{created_at}</td>
                    </tr>
                </table>
                <p><em>This is an automated report generated by the scraping system.</em></p>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_body = f"""
Scraping Report Summary
========================

Report ID: {report_data.get('id', 'N/A')}
Start Date & Time: {start_time}
End Date & Time: {end_time}
Duration: {duration}
Total Pages: {report_data.get('total_pages', 0)}
Total Items: {report_data.get('total_items', 0)}
Success Listing Pages: {report_data.get('success_listing_pages', 0)}
Failed Listing Pages: {report_data.get('failed_listing_pages', 0)}
Success Details Pages: {report_data.get('success_details_pages', 0)}
Failed Details Pages: {report_data.get('failed_details_pages', 0)}
Created At: {created_at}

This is an automated report generated by the scraping system.
        """
        
        # Attach both versions
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email via SMTP server
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg, to_addrs=recipient_emails)
        
        logger.info(f"Email report sent successfully to {', '.join(recipient_emails)}")
        return True
        
    except Exception as e:
        error_msg = f"Error sending email report: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)
>>>>>>> 733c646c44d028f9560ab5e5d232c88ca4792fbd
