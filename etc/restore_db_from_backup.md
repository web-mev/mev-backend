### To restore the database on restart

Note that as part of the `extract_data.sh` script used before destroy, we exported all user files and a SQL dump to a GCP bucket. In addition, we created an on-demand snapshot.

After the new instance is up and running, we can restore the user files by running the `repopulate_data.sh` script. This moves the files, but does NOT do anything about the database. As part of the provisioning process, note that a new database is created and populated with the initial Django superuser.

To restore the database, follow the steps below. Note that the restore process **will overwrite the contents of the new database that was created during provisioning**. Hence, even the Django superuser will change. Thus, a small (and unlikely) gotcha is that the Django superuser email/password will revert to the *older* one that is present in the database snapshot. 

**Instructions**
1. Describe the *target* instance to see whether it has any replicas: 
```
gcloud sql instances describe TARGET_INSTANCE_NAME
```
 Note any instances listed under `replicaNames`. 

2. Delete all replicas, repeating for all:
```
gcloud sql instances delete REPLICA_NAME
```

3. List the backups for the *source* instance:
```
gcloud sql backups list --instance SOURCE_INSTANCE_NAME
```

4. Find the backup you want to use and record its ID value. Note that you should only choose a backup that is marked `SUCCESSFUL`.

5. Restore from the specified backup to the target instance:
```
gcloud sql backups restore BACKUP_ID \
--restore-instance=TARGET_INSTANCE_NAME \
--backup-instance=SOURCE_INSTANCE_NAME
```
After the restore completes, recreate any replicas you deleted previously.