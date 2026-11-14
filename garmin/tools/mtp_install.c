#include <libmtp.h>
#include <CommonCrypto/CommonDigest.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
static int hash(const char *p,char out[65]){FILE *f=fopen(p,"rb");if(!f)return -1;CC_SHA256_CTX c;CC_SHA256_Init(&c);unsigned char b[1024*1024],d[32];size_t n;while((n=fread(b,1,sizeof b,f)))CC_SHA256_Update(&c,b,(CC_LONG)n);int err=ferror(f);fclose(f);if(err)return -1;CC_SHA256_Final(d,&c);for(int i=0;i<32;i++)sprintf(out+2*i,"%02x",d[i]);return 0;}
static int progress(uint64_t sent,uint64_t total,const void *data){uint64_t *last=(uint64_t *)data;if(sent-*last>64*1024*1024||sent==total){printf("PROGRESS\t%llu\t%llu\n",(unsigned long long)sent,(unsigned long long)total);fflush(stdout);*last=sent;}return 0;}
static void release_files(LIBMTP_file_t *p){while(p){LIBMTP_file_t *n=p->next;LIBMTP_destroy_file_t(p);p=n;}}
int main(int argc,char **argv){
 if(argc!=7){fprintf(stderr,"model storage folder source readback final-name required\n");return 2;}
 char expected[65],actual[65];struct stat statbuf;if(stat(argv[4],&statbuf)||hash(argv[4],expected))return 3;
 LIBMTP_Init();LIBMTP_raw_device_t *raw=NULL;int count=0;if(LIBMTP_Detect_Raw_Devices(&raw,&count)!=LIBMTP_ERROR_NONE)return 4;
 for(int i=0;i<count;i++){
  LIBMTP_mtpdevice_t *d=LIBMTP_Open_Raw_Device_Uncached(&raw[i]);if(!d)continue;char *model=LIBMTP_Get_Modelname(d);
  if(!model||strcmp(model,argv[1])){free(model);LIBMTP_Release_Device(d);continue;}
  uint32_t storage=(uint32_t)strtoul(argv[2],NULL,10),folder=(uint32_t)strtoul(argv[3],NULL,10);int result=5;LIBMTP_file_t *before=NULL,*sent=NULL,*after=NULL;uint64_t done=0;uint32_t existing=0;
  if(LIBMTP_Get_Storage(d,0))goto close;
  int enough=0;for(LIBMTP_devicestorage_t *s=d->storage;s;s=s->next)if(s->id==storage&&s->FreeSpaceInBytes>(uint64_t)statbuf.st_size+64*1024*1024)enough=1;
  if(!enough){fprintf(stderr,"Insufficient space in selected storage\n");goto close;}
  before=LIBMTP_Get_Files_And_Folders(d,storage,folder);
  char staging[200];snprintf(staging,sizeof staging,"%s.uploading",argv[6]);
  for(LIBMTP_file_t *f=before;f;f=f->next){if(!strcmp(f->filename,staging)){fprintf(stderr,"Existing staged upload requires review\n");goto close;}if(!strcmp(f->filename,argv[6]))existing=f->item_id;}
  if(existing){sent=LIBMTP_Get_Filemetadata(d,existing);if(!sent)goto close;}
  else{
   sent=LIBMTP_new_file_t();sent->filename=strdup(staging);sent->filesize=statbuf.st_size;sent->filetype=LIBMTP_FILETYPE_UNKNOWN;sent->storage_id=storage;sent->parent_id=folder;sent->modificationdate=time(NULL);
   printf("UPLOADING\t%s\t%u\t%u\n",model,storage,folder);fflush(stdout);
   if(LIBMTP_Send_File_From_File(d,argv[4],sent,progress,&done)){LIBMTP_Dump_Errorstack(d);goto close;}
  }
  done=0;if(LIBMTP_Get_File_To_File(d,sent->item_id,argv[5],progress,&done)){LIBMTP_Dump_Errorstack(d);goto close;}
  if(hash(argv[5],actual)||strcmp(actual,expected)){fprintf(stderr,"Readback checksum mismatch; staged file not activated\n");goto close;}
  if(!existing&&LIBMTP_Set_File_Name(d,sent,argv[6])){LIBMTP_Dump_Errorstack(d);goto close;}
  after=LIBMTP_Get_Files_And_Folders(d,storage,folder);int installed=0;
  for(LIBMTP_file_t *a=after;a;a=a->next)if(!strcmp(a->filename,argv[6])&&a->filesize==(uint64_t)statbuf.st_size)installed=1;
  if(!installed)goto close;
  for(LIBMTP_file_t *b=before;b;b=b->next){int found=0;for(LIBMTP_file_t *a=after;a;a=a->next)if(a->item_id==b->item_id&&a->filesize==b->filesize&&!strcmp(a->filename,b->filename))found=1;if(!found){fprintf(stderr,"Existing folder entry changed\n");goto close;}}
  printf("INSTALLED\t%s\t%u\t%u\t%u\t%llu\t%s\t%s\n",model,storage,folder,sent->item_id,(unsigned long long)statbuf.st_size,expected,argv[6]);fflush(stdout);result=0;
 close:
  release_files(before);release_files(after);if(sent)LIBMTP_destroy_file_t(sent);free(model);LIBMTP_Release_Device(d);free(raw);return result;
 }
 free(raw);fprintf(stderr,"Requested device is not available\n");return 6;
}
