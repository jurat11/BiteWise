import csv
from google.cloud import firestore

def export_users_to_csv(filename='user_export.csv'):
    db = firestore.Client()
    users = list(db.collection('users').stream())
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['telegram_id', 'telegram_username', 'name', 'age'])
        for u in users:
            data = u.to_dict()
            writer.writerow([
                u.id,
                data.get('telegram_username', ''),
                data.get('name', ''),
                data.get('age', '')
            ])
    print(f'Exported {len(users)} users to {filename}')

if __name__ == '__main__':
    export_users_to_csv() 