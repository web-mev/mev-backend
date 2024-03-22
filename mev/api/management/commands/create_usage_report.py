import pandas as pd
import datetime
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage

from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import seaborn as sns

from api.models import ExecutedOperation


class Command(BaseCommand):
    help = ('Prepares a usage report')

    def add_arguments(self, parser):
        pass

    def process_and_plot(self, df, target_col, ylabel):
        '''
        Creates a cumulative distribution plot based on a datetime object contained in
        the `target_col` column of `df`
        '''
        df['year_and_month'] = df[target_col].apply(lambda x: f'{x.year}-{x.month}') 

        monthly_counts = pd.DataFrame(df.year_and_month.value_counts())
        monthly_counts.reset_index(inplace=True)
        monthly_counts['year'] = monthly_counts.year_and_month.apply(lambda x: int(x.split('-')[0]))
        monthly_counts['month'] = monthly_counts.year_and_month.apply(lambda x: int(x.split('-')[1]))
        monthly_counts = monthly_counts.sort_values(by=['year', 'month'])
        
        fig, ax = plt.subplots(figsize=(8,5))
        ax.plot(monthly_counts.year_and_month, monthly_counts['count'].cumsum())
        plt.xticks(rotation=90)
        ax.set_ylabel(ylabel)
        ax.set_xlabel('Month')
        return fig

    def plot_job_distribution(self, op_data):
        '''
        Creates a plot of the types of jobs run
        '''
        vc = op_data.name.value_counts()
        fig, ax = plt.subplots(figsize=(12,5))
        sns.barplot(x=vc.index, y=vc)
        plt.xticks(rotation=90)
        ax.set_ylabel('Count')
        ax.set_xlabel('')
        return fig

    def handle(self, *args, **options):

        datestamp = datetime.datetime.now().strftime('%Y%m%d')
        all_users = get_user_model().objects.all()
        user_data = pd.DataFrame()
        for u in all_users:
            user_data = pd.concat([user_data, pd.Series({
                'pk': str(u.pk),
                'date_joined': u.date_joined,
                'last_login': u.last_login
            })],axis=1)

        fname = f'user_data.{datestamp}.csv'
        fpath = f'reports/{fname}'
        user_data = user_data.T
        user_data.to_csv(fname, index=False)
        with open(fname, 'r') as fin:
            default_storage.save(fpath, fin)
        os.remove(fname)

        # now extract/export info on the jobs run:
        all_ops = ExecutedOperation.objects.all()
        op_data = pd.DataFrame()
        for op in all_ops:
            op_data = pd.concat([op_data, pd.Series({
                'name': op.operation.name,
                'user': str(op.owner.pk),
                'start_datetime': op.execution_start_datetime,
                'stop_datetime': op.execution_stop_datetime
            })], axis=1)

        fname = f'op_data.{datestamp}.csv'
        fpath = f'reports/{fname}'
        op_data = op_data.T
        op_data.to_csv(fname, index=False)

        with open(fname, 'r') as fin:
            default_storage.save(fpath, fin)

        os.remove(fname)

        fname = f'report.{datestamp}.pdf'
        pp = PdfPages(fname)
        fig1 = self.process_and_plot(user_data, 'date_joined', 'Cumulative users')
        fig2 = self.process_and_plot(op_data, 'start_datetime', 'Cumulative jobs')
        fig3 = self.plot_job_distribution(op_data)
        pp.savefig(fig1, bbox_inches='tight')
        pp.savefig(fig2, bbox_inches='tight')
        pp.savefig(fig3, bbox_inches='tight')
        pp.close()

        fpath = f'reports/{fname}'
        with open(fname, 'rb') as fin:
            default_storage.save(fpath, fin)