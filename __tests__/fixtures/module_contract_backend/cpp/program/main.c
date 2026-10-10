#include <stdio.h>
extern int chain_value(void);
int main(void) { FILE *asset = fopen("assets/value.txt", "r"); if (!asset) return 1; fclose(asset); printf("%d\n", chain_value()); return 0; }
