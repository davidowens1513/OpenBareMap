#include <libmtp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
static void release_files(LIBMTP_file_t *p){while(p){LIBMTP_file_t *n=p->next;LIBMTP_destroy_file_t(p);p=n;}}
int main(int argc,char **argv){
 LIBMTP_Init();LIBMTP_raw_device_t *raw=NULL;int count=0;
 if(LIBMTP_Detect_Raw_Devices(&raw,&count)!=LIBMTP_ERROR_NONE){fprintf(stderr,"No MTP devices available\n");return 2;}
 int result=0;
 for(int i=0;i<count;i++){
  LIBMTP_mtpdevice_t *d=LIBMTP_Open_Raw_Device_Uncached(&raw[i]);if(!d){result=3;continue;}
  char *model=LIBMTP_Get_Modelname(d),*serial=LIBMTP_Get_Serialnumber(d);
  printf("DEVICE\t%d\t%s\t%s\n",i,model?model:"unknown",serial?serial:"unknown");fflush(stdout);
  if(LIBMTP_Get_Storage(d,0)!=0){LIBMTP_Dump_Errorstack(d);result=4;goto close;}
  for(LIBMTP_devicestorage_t *st=d->storage;st;st=st->next){
   printf("STORAGE\t%d\t%u\t%llu\t%s\n",i,st->id,(unsigned long long)st->FreeSpaceInBytes,st->StorageDescription?st->StorageDescription:"");
   LIBMTP_file_t *root=LIBMTP_Get_Files_And_Folders(d,st->id,LIBMTP_FILES_AND_FOLDERS_ROOT);
   for(LIBMTP_file_t *f=root;f;f=f->next)if(f->filetype==LIBMTP_FILETYPE_FOLDER&&f->filename&&!strcasecmp(f->filename,"Garmin")){
    printf("GARMIN\t%d\t%u\t%u\n",i,st->id,f->item_id);
    LIBMTP_file_t *maps=LIBMTP_Get_Files_And_Folders(d,st->id,f->item_id);
    for(LIBMTP_file_t *m=maps;m;m=m->next)if(m->filename&&strlen(m->filename)>4&&!strcasecmp(m->filename+strlen(m->filename)-4,".img"))printf("MAP\t%d\t%u\t%llu\t%s\n",i,m->item_id,(unsigned long long)m->filesize,m->filename);
    release_files(maps);
   }
   release_files(root);
  }
 close:
  free(model);free(serial);LIBMTP_Release_Device(d);fflush(stdout);
 }
 free(raw);return result;
}
